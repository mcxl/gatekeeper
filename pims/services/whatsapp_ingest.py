"""WhatsApp chat-export importer for PIMS observations.

V1 supports iOS WhatsApp export ZIPs containing ``_chat.txt`` and JPG/PNG
photo attachments. It is a client of the existing PIMS observation endpoint;
it does not write Supabase directly.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import re
import time
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

import httpx
from PIL import Image, ImageOps

log = logging.getLogger(__name__)

Tenant = Literal["rpd"]

DEFAULT_BASE_URL = ""
DEFAULT_TIMEZONE = "Australia/Sydney"
DEFAULT_DEDUPE_LOG = Path(__file__).resolve().parent.parent / "data" / "whatsapp_ingest_log.jsonl"
DEFAULT_SSA_EVIDENCE_DIR = Path(r"G:\My Drive\alan_mcxico\SSA-evidence")

PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".webp"}
AUDIT_REF_RE = re.compile(r"^[A-Za-z0-9_-]+$")
LINE_RE = re.compile(r"^\[(?P<ts>[^\]]+)\]\s+(?P<author>[^:]+):\s*(?P<body>.*)$")
ATTACH_RE = re.compile(r"<attached:\s*([^>]+)>", re.IGNORECASE)
WHATSAPP_PHOTO_PREFIX_RE = re.compile(r"^\d{8}-PHOTO-", re.IGNORECASE)

# Banner / metadata-photo captions that are not real audit findings.
# Matched against the photo caption (case-insensitive). When any pattern
# matches, the photo is dropped at parse time so it never reaches the
# enricher and never appears in pims_observations as a finding.
_BANNER_CAPTION_PATTERNS = [
    re.compile(r"\bproject\s+value\b", re.IGNORECASE),  # "...project value greater than $250,000"
    re.compile(r"\b(gt|lt)[_\s-]?250k\b", re.IGNORECASE),  # gt_250k / lt-250k tags
    re.compile(r"^\s*\$\s*\d", re.IGNORECASE),  # caption is just a dollar amount like "$250,000"
]
# Address-only banner caption (street number + street + suburb). Kept
# conservative so legitimate observations like "Person on roof at 33 Linda
# St" are not filtered. Triggers only when the caption is short (<=60 chars)
# AND matches the strict address shape.
_BANNER_ADDRESS_RE = re.compile(
    r"^\s*\d{1,5}[A-Za-z]?\s+"                # street number, optional letter
    r"(?:[A-Za-z'\-]+\s+){1,4}"               # 1-4 street name tokens
    r"(?:St|Street|Ave|Avenue|Rd|Road|Ln|Lane|Cl|Close|Cres|Crescent|"
    r"Hwy|Highway|Dr|Drive|Pl|Place|Pde|Parade|Tce|Terrace|Ct|Court|Bvd|Boulevard)"
    r"\.?\s*,?\s*"                            # optional comma
    r"(?:[A-Za-z'\-]+\s*){0,3}\s*$",          # optional suburb
    re.IGNORECASE,
)


def _is_banner_caption(text: str | None) -> bool:
    if not text:
        return False
    s = text.strip()
    if not s:
        return False
    for pat in _BANNER_CAPTION_PATTERNS:
        if pat.search(s):
            return True
    if len(s) <= 60 and _BANNER_ADDRESS_RE.match(s):
        return True
    return False

_CONTROL_CHARS = {
    "\u200e": "",
    "\u200f": "",
    "\u202a": "",
    "\u202b": "",
    "\u202c": "",
    "\u202d": "",
    "\u202e": "",
}
_SYSTEM_MARKERS = (
    "created group",
    "messages and calls are end-to-end encrypted",
)


@dataclass(frozen=True)
class WaMessage:
    timestamp: datetime
    author: str
    body: str
    attachment_filename: str | None = None
    caption: str | None = None
    audit_ref: str | None = None
    project_value: str | None = None
    site: str | None = None


@dataclass(frozen=True)
class PreparedObservation:
    message: WaMessage
    payload: dict
    dedupe_key: str
    photo_sha256: str
    source_filename: str
    evidence_filename: str


@dataclass
class IngestResult:
    zip_path: str
    audit_ref: str | None
    parsed: int = 0
    posted: int = 0
    skipped: int = 0
    dry_run: bool = False
    observation_ids: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    payloads: list[dict] = field(default_factory=list)
    evidence_dir: str | None = None


def _clean_text(text: str) -> str:
    for src, repl in _CONTROL_CHARS.items():
        text = text.replace(src, repl)
    text = text.replace("\u202f", " ").replace("\xa0", " ")
    return text.strip()


def slug_audit_ref(value: str) -> str:
    """Return a PIMS-safe audit_ref slug."""
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", _clean_text(value))
    slug = re.sub(r"-{2,}", "-", slug).strip("-_")
    return slug


def validate_audit_ref(value: str) -> str:
    if not AUDIT_REF_RE.match(value):
        raise ValueError(f"audit_ref must match {AUDIT_REF_RE.pattern}: {value!r}")
    return value


def clean_whatsapp_filename(filename: str) -> str:
    """Return a user-friendly filename while preserving the real extension."""
    name = Path(filename).name
    return WHATSAPP_PHOTO_PREFIX_RE.sub("", name)


def _parse_timestamp(raw: str, timezone: str) -> datetime:
    cleaned = _clean_text(raw).lower().replace(".", "")
    formats = (
        "%d/%m/%Y, %I:%M:%S %p",
        "%d/%m/%y, %I:%M:%S %p",
        "%d/%m/%Y, %H:%M:%S",
        "%d/%m/%y, %H:%M:%S",
    )
    last_error: Exception | None = None
    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt).replace(tzinfo=ZoneInfo(timezone))
        except ValueError as exc:
            last_error = exc
    raise ValueError(f"Unsupported WhatsApp timestamp {raw!r}") from last_error


def _normalise_project_value(value: str) -> str | None:
    value = _clean_text(value).lower().replace(" ", "")
    if value in {"gt_250k", ">250k", "greaterthan250k", "high"}:
        return "gt_250k"
    if value in {"lt_250k", "<250k", "lessthan250k", "low"}:
        return "lt_250k"
    log.warning("Ignoring unrecognised WhatsApp PROJECT_VALUE: %r", value)
    return None


def _strip_attachment_marker(body: str) -> tuple[str, str | None]:
    m = ATTACH_RE.search(body)
    if not m:
        return body.strip(), None
    filename = _clean_text(m.group(1))
    text = (body[:m.start()] + body[m.end():]).strip()
    return text, filename


def _is_system_line(author: str, body: str) -> bool:
    haystack = f"{author}: {body}".lower()
    return any(marker in haystack for marker in _SYSTEM_MARKERS)


def _read_chat(zip_path: Path) -> str:
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        chat_name = next((n for n in names if Path(n).name == "_chat.txt"), None)
        if chat_name is None:
            raise ValueError("WhatsApp export zip does not contain _chat.txt")
        data = zf.read(chat_name)
    for encoding in ("utf-8-sig", "utf-8", "utf-16"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def parse_chat(
    zip_path: Path,
    *,
    audit_ref: str | None = None,
    timezone: str = DEFAULT_TIMEZONE,
) -> list[WaMessage]:
    """Parse photo observations from a WhatsApp export zip."""
    override_ref = validate_audit_ref(slug_audit_ref(audit_ref)) if audit_ref else None
    current_ref: str | None = override_ref
    current_project_value: str | None = None
    current_site: str | None = None
    messages: list[WaMessage] = []

    last_photo_idx: int | None = None
    last_plain: WaMessage | None = None

    for raw_line in _read_chat(zip_path).splitlines():
        line = _clean_text(raw_line)
        if not line:
            continue
        m = LINE_RE.match(line)
        if not m:
            continue

        ts = _parse_timestamp(m.group("ts"), timezone)
        author = _clean_text(m.group("author"))
        body = _clean_text(m.group("body"))
        if _is_system_line(author, body):
            continue

        body_without_attachment, attachment = _strip_attachment_marker(body)
        control = body_without_attachment.strip()
        control_match = re.match(r"^(AUDIT|PROJECT_VALUE|SITE)\s*:\s*(.+)$", control, re.IGNORECASE)
        if control_match and attachment is None:
            key = control_match.group(1).upper()
            value = control_match.group(2).strip()
            if key == "AUDIT":
                current_ref = validate_audit_ref(slug_audit_ref(value))
            elif key == "PROJECT_VALUE":
                current_project_value = _normalise_project_value(value)
            elif key == "SITE":
                current_site = value
            last_plain = None
            continue

        if attachment:
            ext = Path(attachment).suffix.lower()
            if ext not in PHOTO_EXTS:
                last_plain = None
                continue
            caption = body_without_attachment or None
            if caption is None and last_plain is not None:
                same_author = last_plain.author == author
                delta = abs((ts - last_plain.timestamp).total_seconds())
                if same_author and delta <= 60:
                    caption = last_plain.body
            # Skip banner/metadata photos (project-value declarations,
            # address-only context shots) — they are not audit findings.
            if _is_banner_caption(caption):
                log.info(
                    "Skipping banner photo at %s: caption=%r filename=%s",
                    ts.isoformat(), caption, attachment,
                )
                last_plain = None
                continue
            messages.append(WaMessage(
                timestamp=ts,
                author=author,
                body=body_without_attachment,
                attachment_filename=attachment,
                caption=caption,
                audit_ref=current_ref,
                project_value=current_project_value,
                site=current_site,
            ))
            last_photo_idx = len(messages) - 1
            last_plain = None
            continue

        if control and last_photo_idx is not None:
            prev = messages[last_photo_idx]
            same_author = prev.author == author
            delta = abs((ts - prev.timestamp).total_seconds())
            if same_author and delta <= 60 and not prev.caption:
                messages[last_photo_idx] = WaMessage(
                    timestamp=prev.timestamp,
                    author=prev.author,
                    body=prev.body,
                    attachment_filename=prev.attachment_filename,
                    caption=control,
                    audit_ref=prev.audit_ref,
                    project_value=prev.project_value,
                    site=prev.site,
                )
                last_plain = None
                continue

        last_plain = WaMessage(timestamp=ts, author=author, body=control)

    if override_ref:
        messages = [
            WaMessage(
                timestamp=m.timestamp,
                author=m.author,
                body=m.body,
                attachment_filename=m.attachment_filename,
                caption=m.caption,
                audit_ref=override_ref,
                project_value=m.project_value,
                site=m.site,
            )
            for m in messages
        ]

    return messages


def _extract_attachment(zip_path: Path, filename: str) -> bytes:
    target = filename.replace("\\", "/")
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        exact = next((n for n in names if n == target), None)
        if exact:
            return zf.read(exact)
        basename_matches = [n for n in names if Path(n).name == Path(filename).name]
        if not basename_matches:
            raise FileNotFoundError(f"Attachment not found in zip: {filename}")
        if len(basename_matches) > 1:
            raise ValueError(
                f"Attachment basename is ambiguous in zip: {filename} "
                f"matches {basename_matches!r}"
            )
        return zf.read(basename_matches[0])


def _prepare_photo_base64(photo_bytes: bytes) -> tuple[str, str]:
    sha256 = hashlib.sha256(photo_bytes).hexdigest()
    with Image.open(BytesIO(photo_bytes)) as im:
        im = ImageOps.exif_transpose(im)
        longest = max(im.width, im.height)
        if longest > 2048:
            ratio = 2048 / float(longest)
            im = im.resize(
                (max(1, int(im.width * ratio)), max(1, int(im.height * ratio))),
                Image.LANCZOS,
            )
        buf = BytesIO()
        im.convert("RGB").save(buf, format="JPEG", quality=85)
    encoded = base64.standard_b64encode(buf.getvalue()).decode("ascii")
    if len(encoded) >= 20_000_000:
        raise ValueError("Prepared photo_base64 exceeds PIMS size cap")
    return encoded, sha256


def _dedupe_key(audit_ref: str, ts: datetime, filename: str) -> str:
    raw = f"{audit_ref}|{ts.isoformat()}|{filename}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _audit_date_from_observations(observations: list[PreparedObservation]) -> str:
    if observations:
        return observations[0].message.timestamp.date().isoformat()
    return datetime.now(tz=ZoneInfo(DEFAULT_TIMEZONE)).date().isoformat()


def _next_audit_folder(root: Path, audit_date: str, audit_ref: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    prefix = f"{audit_date}-RPD-"
    unmarked: list[Path] = []
    for folder in sorted(root.glob(f"{prefix}[0-9][0-9]")):
        marker = folder / ".whatsapp_audit_ref"
        if marker.exists():
            try:
                if marker.read_text(encoding="utf-8").strip() == audit_ref:
                    return folder
            except OSError:
                pass
        else:
            unmarked.append(folder)
    if len(unmarked) == 1:
        marker = unmarked[0] / ".whatsapp_audit_ref"
        marker.write_text(audit_ref + "\n", encoding="utf-8")
        return unmarked[0]
    existing_nums: list[int] = []
    for folder in root.glob(f"{prefix}[0-9][0-9]"):
        try:
            existing_nums.append(int(folder.name.rsplit("-", 1)[-1]))
        except ValueError:
            continue
    next_num = max(existing_nums, default=0) + 1
    folder = root / f"{prefix}{next_num:02d}"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / ".whatsapp_audit_ref").write_text(audit_ref + "\n", encoding="utf-8")
    return folder


def export_evidence_photos(
    zip_path: Path,
    observations: list[PreparedObservation],
    *,
    evidence_root: Path = DEFAULT_SSA_EVIDENCE_DIR,
) -> Path | None:
    if not observations:
        return None
    audit_ref = observations[0].payload["audit_ref"]
    audit_date = _audit_date_from_observations(observations)
    audit_folder = _next_audit_folder(evidence_root, audit_date, audit_ref)
    photos_dir = audit_folder / f"{audit_folder.name}-photos"
    photos_dir.mkdir(parents=True, exist_ok=True)
    for obs in observations:
        data = _extract_attachment(zip_path, obs.source_filename)
        target = photos_dir / obs.evidence_filename
        if target.exists() and target.read_bytes() == data:
            continue
        if target.exists():
            stem = target.stem
            suffix = target.suffix
            i = 2
            while target.exists():
                target = photos_dir / f"{stem}-{i}{suffix}"
                i += 1
        target.write_bytes(data)
    return audit_folder


def load_dedupe(log_path: Path = DEFAULT_DEDUPE_LOG) -> tuple[set[str], set[tuple[str, str]]]:
    keys: set[str] = set()
    photos: set[tuple[str, str]] = set()
    if not log_path.exists():
        return keys, photos
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("dedupe_key"):
            keys.add(str(row["dedupe_key"]))
        if row.get("audit_ref") and row.get("sha256"):
            photos.add((str(row["audit_ref"]), str(row["sha256"])))
    return keys, photos


def append_dedupe(
    *,
    log_path: Path,
    audit_ref: str,
    ts: datetime,
    filename: str,
    sha256: str,
    dedupe_key: str,
    observation_id: str | None,
    dry_run: bool = False,
) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "audit_ref": audit_ref,
        "ts": ts.isoformat(),
        "filename": filename,
        "sha256": sha256,
        "dedupe_key": dedupe_key,
        "observation_id": observation_id,
        "posted_at": datetime.now(tz=ZoneInfo(DEFAULT_TIMEZONE)).isoformat(),
        "dry_run": dry_run,
    }
    with log_path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def to_observation_payload(msg: WaMessage, zip_path: Path) -> PreparedObservation:
    if not msg.audit_ref:
        raise ValueError("Message has no audit_ref; add an AUDIT block or pass --audit-ref")
    if not msg.attachment_filename:
        raise ValueError("Message has no photo attachment")
    audit_ref = validate_audit_ref(slug_audit_ref(msg.audit_ref))
    photo_bytes = _extract_attachment(zip_path, msg.attachment_filename)
    photo_base64, photo_sha256 = _prepare_photo_base64(photo_bytes)
    caption = (msg.caption or "").strip() or f"Photo observation: {msg.attachment_filename}"
    payload = {
        "audit_ref": audit_ref,
        "observation_text": caption[:2000],
        "observation_date": msg.timestamp.isoformat(),
        "photo_base64": photo_base64,
        "filename": clean_whatsapp_filename(msg.attachment_filename),
        "submitted_by": msg.author,
        "device_info": "whatsapp-export",
    }
    return PreparedObservation(
        message=msg,
        payload=payload,
        dedupe_key=_dedupe_key(audit_ref, msg.timestamp, msg.attachment_filename),
        photo_sha256=photo_sha256,
        source_filename=msg.attachment_filename,
        evidence_filename=clean_whatsapp_filename(msg.attachment_filename),
    )


class RateLimiter:
    def __init__(self, requests_per_minute: int = 25) -> None:
        self.interval = 60.0 / requests_per_minute
        self._last = 0.0

    def wait(self) -> None:
        now = time.monotonic()
        remaining = self.interval - (now - self._last)
        if remaining > 0:
            time.sleep(remaining)
        self._last = time.monotonic()


def _post_payload(
    client: httpx.Client,
    *,
    base_url: str,
    token: str,
    payload: dict,
    limiter: RateLimiter,
) -> str | None:
    url = f"{base_url.rstrip('/')}/pims/observation/rpd"
    headers = {"X-PIMS-Token": token}
    delays = [1, 2, 4, 8]
    attempt = 0
    while True:
        limiter.wait()
        try:
            res = client.post(url, headers=headers, json=payload)
        except httpx.TransportError:
            if attempt >= len(delays):
                raise
            time.sleep(delays[attempt])
            attempt += 1
            continue
        if res.status_code not in {429, 500, 502, 503, 504}:
            res.raise_for_status()
            data = res.json() if res.content else {}
            obs_id = data.get("id") if isinstance(data, dict) else None
            return str(obs_id) if obs_id else None
        if attempt >= len(delays):
            res.raise_for_status()
        retry_after = res.headers.get("Retry-After")
        if retry_after:
            try:
                delay = float(retry_after)
            except ValueError:
                delay = delays[attempt]
        else:
            delay = delays[attempt]
        time.sleep(delay)
        attempt += 1


def ingest_zip(
    zip_path: Path,
    *,
    audit_ref: str | None = None,
    tenant: Tenant = "rpd",
    base_url: str | None = None,
    token: str | None = None,
    timezone: str = DEFAULT_TIMEZONE,
    dedupe_log: Path = DEFAULT_DEDUPE_LOG,
    evidence_root: Path | None = None,
    dry_run: bool = False,
) -> IngestResult:
    if tenant != "rpd":
        raise ValueError("WhatsApp importer v1 supports tenant='rpd' only")
    zip_path = Path(zip_path)
    messages = parse_chat(zip_path, audit_ref=audit_ref, timezone=timezone)
    result = IngestResult(
        zip_path=str(zip_path),
        audit_ref=slug_audit_ref(audit_ref) if audit_ref else None,
        parsed=len(messages),
        dry_run=dry_run,
    )
    seen_keys, seen_photos = load_dedupe(dedupe_log)
    prepared: list[PreparedObservation] = []
    evidence_candidates: list[PreparedObservation] = []
    for msg in messages:
        obs = to_observation_payload(msg, zip_path)
        evidence_candidates.append(obs)
        audit = obs.payload["audit_ref"]
        result.audit_ref = result.audit_ref or audit
        if obs.dedupe_key in seen_keys or (audit, obs.photo_sha256) in seen_photos:
            result.skipped += 1
            continue
        prepared.append(obs)
        seen_keys.add(obs.dedupe_key)
        seen_photos.add((audit, obs.photo_sha256))

    if dry_run:
        result.payloads = [p.payload for p in prepared]
        result.posted = len(prepared)
        return result

    token = token or os.getenv("PIMS_RPD_TOKEN", "")
    if not token:
        raise ValueError("PIMS_RPD_TOKEN is required unless --dry-run is used")
    base_url = base_url or os.getenv("PIMS_BASE_URL") or DEFAULT_BASE_URL
    if not base_url:
        raise ValueError("PIMS_BASE_URL or --base-url is required unless --dry-run is used")
    limiter = RateLimiter(25)
    posted_observations: list[PreparedObservation] = []
    with httpx.Client(timeout=60) as client:
        for obs in prepared:
            observation_id = _post_payload(
                client,
                base_url=base_url,
                token=token,
                payload=obs.payload,
                limiter=limiter,
            )
            append_dedupe(
                log_path=dedupe_log,
                audit_ref=obs.payload["audit_ref"],
                ts=obs.message.timestamp,
                filename=obs.message.attachment_filename or "",
                sha256=obs.photo_sha256,
                dedupe_key=obs.dedupe_key,
                observation_id=observation_id,
            )
            result.posted += 1
            posted_observations.append(obs)
            if observation_id:
                result.observation_ids.append(observation_id)
    try:
        evidence_dir = export_evidence_photos(
            zip_path,
            evidence_candidates,
            evidence_root=evidence_root or Path(os.getenv("PIMS_SSA_EVIDENCE_DIR", str(DEFAULT_SSA_EVIDENCE_DIR))),
        )
        if evidence_dir is not None:
            result.evidence_dir = str(evidence_dir)
    except Exception as exc:
        log.exception("SSA evidence photo export failed for %s", zip_path)
        result.errors.append(f"evidence_export_failed: {type(exc).__name__}: {exc}")
    return result


def build_sample_zip(chat_path: Path, media_paths: list[Path], out_path: Path) -> Path:
    """Utility for manual smoke tests; not used by the watcher."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(chat_path, "_chat.txt")
        for p in media_paths:
            zf.write(p, p.name)
    return out_path
