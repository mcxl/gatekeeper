#!/usr/bin/env python
"""
pims_pdf_import.py — Extract observations from RPD site audit PDFs.

Usage:
  python pims_pdf_import.py --pdf <path>          # dry-run (default)
  python pims_pdf_import.py --pdf <path> --dry-run
  python pims_pdf_import.py --folder <path>
  python pims_pdf_import.py --pdf <path> --insert  # write to Supabase

Dependencies: pdfplumber, python-dotenv, requests
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

import pdfplumber


# ── Constants & patterns ───────────────────────────────────────────────────────

SKIP_PATTERNS = [
    re.compile(r"How 1Breadcrumb Resolves", re.IGNORECASE),
    re.compile(r"Implementing the SDS upload workflow", re.IGNORECASE),
    re.compile(r"The correct process, as shown in", re.IGNORECASE),
    re.compile(r"SDS upload workflow extracted from", re.IGNORECASE),
    re.compile(r"Notes\s*[-–]\s*Silica", re.IGNORECASE),
    re.compile(r"Reference:\s*AS/NZS\s*1576", re.IGNORECASE),
    re.compile(r"How to Add Safety Data Sheets", re.IGNORECASE),
    re.compile(r"^File summary", re.IGNORECASE),
    re.compile(r"^Media summary", re.IGNORECASE),
    re.compile(r"^Photo \d+\s+Photo \d+$"),
]

KNOWN_SECTIONS = [
    "Planning and site establishment",
    "Planning and risk management",
    "Worker competency and PPE",
    "Plant and equipment safety",
    "Site security and other controls",
    "Hazardous substances and silica control",
    "Demolition and temporary support",
    "General work at height",
    "General site",
]

# Build regex that matches section names (with optional "Site Inspection / " prefix).
# Section banners end with: score suffix, "N flagged", "(project value...)", or EOL.
# This prevents matching criterion text that happens to start with a section name
# (e.g. "General site emergency - communicated to workers...").
_sec_alts = "|".join(re.escape(s) for s in KNOWN_SECTIONS)
SECTION_BANNER_RE = re.compile(
    rf"^(?:Site Inspection\s*/\s*)?({_sec_alts})"
    rf"(?:\s*\(project[^)]*\))?"   # optional "(project value <$250K)" qualifier
    rf"(?:\s+\d[\d\s/()%.flagged,]*)?$",  # optional score/flagged suffix then EOL
    re.IGNORECASE,
)

SUBSCORE_RE = re.compile(r"\d+\s+flagged,\s*\d+\s*/\s*\d+\s*\(\d+\.?\d*%\)")
SCORE_SUFFIX_RE = re.compile(r"\s+\d+\s*/\s*\d+\s*\(\d+\.?\d*%\).*$")
SITE_INSPECTION_SCORE_RE = re.compile(
    r"^Site Inspection\s+\d+\s+flagged,\s*\d+\s*/\s*\d+\s*\(\d+\.?\d*%\)",
    re.IGNORECASE,
)
STATUS_RE = re.compile(r"\b(Non[- ]?Compliant|Compliant)\b", re.IGNORECASE)
LEGAL_REF_RE = re.compile(r"\((?:WHS\s+(?:Act|Reg)[^)]+|AS[^)]+|CoP[^)]+)\)")
PHOTO_REF_RE = re.compile(r"(Photo\s+\d+)")
DATE_FOOTER_RE = re.compile(r"Date:\s*(\d{1,2}/\d{1,2}/\d{4})")
DATE_LONG_RE = re.compile(
    r"(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})",
    re.IGNORECASE,
)
DATE_ORDINAL_RE = re.compile(
    r"(\d{1,2})(?:st|nd|rd|th)\s+(January|February|March|April|May|June|July"
    r"|August|September|October|November|December)\s+(\d{4})",
    re.IGNORECASE,
)
HEADER_SKIP_RE = re.compile(
    r"^(?:Robertson.s Remedial and Painting|Site Safety Audit\b"
    r"|Robertson.s Remedial and Painting\s*[-–])",
    re.IGNORECASE,
)
PAGE_FOOTER_RE = re.compile(
    r"^Date:\s*\d{1,2}/\d{1,2}/\d{4}\s+Page:\s*\d+\s+of\s+\d+\s+Written By:",
    re.IGNORECASE,
)
FLAGGED_ITEMS_RE = re.compile(r"^Flagged items\s+\d+\s+flagged", re.IGNORECASE)

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10,
    "november": 11, "december": 12,
}

# Lines that are purely structural / not observation content
COMMENT_KEYWORD_RE = re.compile(r"^Comment:?\s*", re.IGNORECASE)
RECOMMENDATION_KEYWORD_RE = re.compile(r"^(?:Recommendation\b|It is recommended\b)", re.IGNORECASE)


# ── Helpers ────────────────────────────────────────────────────────────────────

def normalise_date(raw: str) -> Optional[str]:
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", raw.strip())
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    m = DATE_LONG_RE.search(raw)
    if m:
        mon = MONTH_MAP.get(m.group(2).lower())
        if mon:
            return f"{m.group(3)}-{mon:02d}-{int(m.group(1)):02d}"
    m = DATE_ORDINAL_RE.search(raw)
    if m:
        mon = MONTH_MAP.get(m.group(2).lower())
        if mon:
            return f"{m.group(3)}-{mon:02d}-{int(m.group(1)):02d}"
    return None


def clean_cid(text: str) -> str:
    text = text.replace("(cid:222)", "fi")
    text = re.sub(r"\(cid:\d+\)", "", text)
    return text


def is_skip_line(line: str) -> bool:
    for pat in SKIP_PATTERNS:
        if pat.search(line):
            return True
    return False


def is_noise_line(line: str) -> bool:
    """Lines to silently skip: headers, footers, structural."""
    if not line:
        return True
    if HEADER_SKIP_RE.match(line):
        return True
    if PAGE_FOOTER_RE.match(line):
        return True
    if line == "Complete":
        return True
    if re.match(r"^Score \d+", line):
        return True
    if re.match(r"^Flagged items \d+$", line):
        return True
    return False


def strip_section_score(text: str) -> str:
    """Remove trailing score and 'flagged' suffix from section name."""
    text = SUBSCORE_RE.sub("", text).strip()
    text = SCORE_SUFFIX_RE.sub("", text).strip()
    # Remove trailing "N flagged" that might remain
    text = re.sub(r"\s+\d+\s+flagged\s*$", "", text).strip()
    return text


# ── Metadata extraction ───────────────────────────────────────────────────────

def extract_metadata(pdf: pdfplumber.PDF) -> dict:
    audit_date = None
    site_address = None
    prepared_by = None

    p1_text = clean_cid(pdf.pages[0].extract_text() or "")
    m = DATE_ORDINAL_RE.search(p1_text)
    if m:
        audit_date = normalise_date(m.group(0))

    if not audit_date:
        for p in pdf.pages[:5]:
            text = p.extract_text() or ""
            m = DATE_FOOTER_RE.search(text)
            if m:
                audit_date = normalise_date(m.group(1))
                break

    for p_idx in [2, 1, 3]:
        if p_idx >= len(pdf.pages):
            continue
        text = clean_cid(pdf.pages[p_idx].extract_text() or "")
        for line in text.split("\n"):
            if not site_address and re.match(r"Site conducted\s+", line, re.IGNORECASE):
                site_address = re.sub(r"^Site conducted\s+", "", line, flags=re.IGNORECASE).strip()
            if not prepared_by and re.match(r"Prepared by\s+", line, re.IGNORECASE):
                prepared_by = re.sub(r"^Prepared by\s+", "", line, flags=re.IGNORECASE).strip()
            if not audit_date:
                m2 = re.match(r"Date of inspection\s+(.*)", line, re.IGNORECASE)
                if m2:
                    audit_date = normalise_date(m2.group(1).strip())
        if site_address and prepared_by:
            break

    return {"audit_date": audit_date, "site_address": site_address, "prepared_by": prepared_by}


# ── Two-pass observation parser ───────────────────────────────────────────────
#
# Pass 1: Build a cleaned line list from page 3+, tagging each line with its type.
# Pass 2: Walk through tagged lines to assemble observations.
#
# The key insight: in the PDF, criterion text is left-aligned and the status badge
# floats to the right on one of the criterion lines. pdfplumber concatenates them.
# Lines AFTER the badge line may still be criterion continuation (wrapping from the
# left column). We treat all text between the status badge and the next keyword
# (Comment/Recommendation/Photo/section/next-criterion) as criterion continuation.

def _classify_line(line: str) -> str:
    """Classify a line into a type for the two-pass parser."""
    if not line.strip():
        return "empty"
    line = line.strip()
    if is_noise_line(line):
        return "noise"
    if is_skip_line(line):
        return "skip"
    if SECTION_BANNER_RE.match(line):
        return "section"
    if SITE_INSPECTION_SCORE_RE.match(line):
        return "site_score"
    if FLAGGED_ITEMS_RE.match(line):
        return "flagged_marker"
    if SUBSCORE_RE.match(line.strip()):
        return "subscore"
    if re.match(r"^(Photo\s+\d+\s*)+$", line):
        return "photo_line"
    if re.match(r"^(Site conducted|Prepared by|Date of inspection)\s+", line, re.IGNORECASE):
        return "noise"
    # Status badge must be at end of line (right-aligned in PDF) or sole content
    if STATUS_RE.search(line):
        m = STATUS_RE.search(line)
        after_badge = line[m.end():].strip()
        # Accept if badge is at end of line, or only trailing punctuation/whitespace
        if not after_badge or re.match(r'^[\s.,;:)]*$', after_badge):
            return "has_status"
    if COMMENT_KEYWORD_RE.match(line):
        return "comment_start"
    if RECOMMENDATION_KEYWORD_RE.match(line):
        return "recommendation_start"
    return "text"


def parse_observations(pdf: pdfplumber.PDF) -> tuple[list[dict], list[str]]:
    """Parse observation blocks from page 3 onward."""
    # Collect and clean lines
    raw_lines: list[str] = []
    for p in pdf.pages[2:]:  # page 3+ (0-indexed)
        text = clean_cid(p.extract_text() or "")
        raw_lines.extend(text.split("\n"))

    # Tag each line
    tagged: list[tuple[str, str, str]] = []  # (original, stripped, type)
    for line in raw_lines:
        s = line.strip()
        tagged.append((line, s, _classify_line(s)))

    observations: list[dict] = []
    skipped_blocks: list[str] = []
    current_section: Optional[str] = None
    i = 0
    in_flagged_preamble = False  # Before the full listing starts

    while i < len(tagged):
        orig, s, typ = tagged[i]

        if typ in ("empty", "noise", "subscore", "photo_line"):
            i += 1
            continue

        if typ == "skip":
            skipped_blocks.append(s[:80])
            i += 1
            # Skip until next section or has_status line
            while i < len(tagged):
                _, s2, t2 = tagged[i]
                if t2 in ("section", "has_status", "site_score", "flagged_marker"):
                    break
                i += 1
            continue

        if typ == "flagged_marker":
            in_flagged_preamble = True
            i += 1
            continue

        if typ == "site_score":
            in_flagged_preamble = False
            i += 1
            continue

        if typ == "section":
            m_sec = SECTION_BANNER_RE.match(s)
            if m_sec:
                current_section = strip_section_score(m_sec.group(1))
            # A section banner with a score suffix marks start of full listing
            if SUBSCORE_RE.search(s) or SCORE_SUFFIX_RE.search(s):
                in_flagged_preamble = False
            i += 1
            continue

        # Try to parse an observation starting here
        if typ == "has_status":
            obs, i = _parse_one_observation(tagged, i, current_section, in_flagged_preamble)
            if obs:
                observations.append(obs)
            continue

        # Text line that might be the start of a multi-line criterion
        # Look ahead for a status badge
        if typ in ("text", "comment_start", "recommendation_start"):
            found_badge = False
            for j in range(i + 1, min(i + 15, len(tagged))):
                _, _, tj = tagged[j]
                if tj == "has_status":
                    found_badge = True
                    break
                if tj in ("section", "site_score", "skip", "flagged_marker"):
                    break
            if found_badge:
                obs, i = _parse_one_observation(tagged, i, current_section, in_flagged_preamble)
                if obs:
                    observations.append(obs)
                continue

        i += 1

    return observations, skipped_blocks


def _parse_one_observation(
    tagged: list[tuple[str, str, str]],
    start: int,
    section: Optional[str],
    in_flagged: bool,
) -> tuple[Optional[dict], int]:
    """
    Parse a single observation starting at index `start`.
    Returns (obs_dict, next_index).

    Strategy:
    1. Collect criterion text lines until the line containing the status badge.
    2. On the badge line, text before the badge is criterion; text after is ignored
       (the badge is at the right edge in the PDF).
    3. After the badge line, collect criterion continuation lines until we hit a
       keyword (Comment/Recommendation), photo line, section, or next observation.
    4. Then collect comment/recommendation text.
    """
    criterion_parts: list[str] = []
    status: Optional[str] = None
    i = start

    # Phase 1: collect lines up to and including the status badge line
    while i < len(tagged):
        orig, s, typ = tagged[i]

        if typ in ("empty", "noise"):
            i += 1
            continue
        if typ in ("section", "site_score", "skip", "flagged_marker", "subscore"):
            break  # No observation here after all
        if typ == "photo_line":
            i += 1
            continue

        if typ == "has_status":
            m = STATUS_RE.search(s)
            before = s[:m.start()].strip()
            if before:
                criterion_parts.append(before)
            status_raw = m.group(1)
            status = "NCR" if "non" in status_raw.lower() else "Compliant"
            i += 1
            break

        # Regular text (or comment_start/recommendation_start that happens before a badge)
        criterion_parts.append(s)
        i += 1

    if status is None:
        return None, start + 1

    # Phase 2: collect criterion continuation lines after the badge.
    # These are lines that complete the criterion sentence but appeared below the
    # badge in the PDF's left column. Stop at: Comment, Recommendation, Photo,
    # section banner, next observation (has_status), or skip block.
    while i < len(tagged):
        orig, s, typ = tagged[i]

        if typ in ("empty", "noise"):
            i += 1
            continue
        if typ in ("section", "site_score", "skip", "flagged_marker", "subscore",
                    "has_status", "photo_line", "comment_start", "recommendation_start"):
            break

        # It's a "text" line. Heuristic: if it looks like it continues the criterion
        # sentence (e.g. ends with a legal ref closing paren, or starts lowercase,
        # or is short and completes a phrase), it's continuation.
        # If it's a long block that looks like freeform narrative, it might be an
        # unlabelled comment. We'll treat all text before the first long narrative
        # block as criterion continuation.
        # Simple rule: lines containing legal refs in parens are criterion.
        # Otherwise, treat as criterion continuation only if no comment/recommendation
        # has been seen and the line is short or sentence-completing.
        if LEGAL_REF_RE.search(s) or s.endswith(")") or s.endswith(")."):
            criterion_parts.append(s)
            i += 1
            continue
        # Short continuation (< 80 chars, no sentence-start feel)
        if len(s) < 80 and (s[0].islower() or s.startswith("(")):
            criterion_parts.append(s)
            i += 1
            continue
        # If it starts with a dash/bullet, likely criterion list continuation
        if s.startswith("-") or s.startswith("•") or s.startswith("\uf0b7"):
            criterion_parts.append(s)
            i += 1
            continue
        # Otherwise, this is the start of unlabelled comment text
        break

    criterion_text = " ".join(criterion_parts).strip()

    # Phase 3: collect comment, recommendation, photo refs
    comment_lines: list[str] = []
    recommendation_lines: list[str] = []
    photo_refs: list[str] = []
    collecting = "comment"
    at_break_point = True  # Start as true so first text line can be checked

    while i < len(tagged):
        orig, s, typ = tagged[i]

        if typ in ("empty", "noise"):
            i += 1
            continue
        if typ in ("section", "site_score", "skip", "flagged_marker", "subscore"):
            break
        # Next observation starts
        if typ == "has_status":
            break

        if typ == "photo_line":
            photo_refs.extend(PHOTO_REF_RE.findall(s))
            at_break_point = True
            i += 1
            continue

        # Check if a text line starts a new criterion — but only after a natural
        # break (photo line, empty region). This prevents breaking mid-paragraph.
        if typ == "text" and at_break_point:
            is_new_obs = False
            for j in range(i, min(i + 10, len(tagged))):
                _, _, tj = tagged[j]
                if tj == "has_status":
                    is_new_obs = True
                    break
                if tj in ("section", "site_score", "skip", "flagged_marker",
                          "comment_start", "recommendation_start"):
                    break
            if is_new_obs:
                return _build_obs(criterion_text, status, comment_lines,
                                  recommendation_lines, photo_refs, section, in_flagged), i

        if typ == "photo_line":
            photo_refs.extend(PHOTO_REF_RE.findall(s))
            i += 1
            continue

        if typ == "comment_start":
            collecting = "comment"
            rest = COMMENT_KEYWORD_RE.sub("", s).strip()
            if rest:
                comment_lines.append(rest)
            # After a comment line, the next text could be a new observation
            at_break_point = True
            i += 1
            continue

        if typ == "recommendation_start":
            collecting = "recommendation"
            at_break_point = False
            # Keep "It is recommended..." intact; only strip bare "Recommendation" label
            if re.match(r"^Recommendation\s*$", s, re.IGNORECASE):
                pass  # bare label, content on next lines
            elif re.match(r"^Recommendation\s+", s, re.IGNORECASE):
                rest = re.sub(r"^Recommendation\s+", "", s, flags=re.IGNORECASE).strip()
                if rest:
                    recommendation_lines.append(rest)
            else:
                # "It is recommended..." — keep the full text
                recommendation_lines.append(s)
            i += 1
            continue

        # Text within comment/rec collection
        at_break_point = False
        # Extract any inline photo refs
        inline_photos = PHOTO_REF_RE.findall(s)
        if inline_photos:
            photo_refs.extend(inline_photos)
            text_part = PHOTO_REF_RE.sub("", s).strip()
            if not text_part:
                at_break_point = True  # Photo-only line acts as break
                i += 1
                continue
            s = text_part

        if collecting == "recommendation":
            recommendation_lines.append(s)
        else:
            comment_lines.append(s)
        i += 1

    return _build_obs(criterion_text, status, comment_lines,
                      recommendation_lines, photo_refs, section, in_flagged), i


def _build_obs(
    criterion_text: str,
    status: Optional[str],
    comment_lines: list[str],
    recommendation_lines: list[str],
    photo_refs: list[str],
    section: Optional[str],
    in_flagged: bool,
) -> dict:
    comment = " ".join(comment_lines).strip() or None
    recommendation = " ".join(recommendation_lines).strip() or None
    photo_str = ", ".join(photo_refs) if photo_refs else None

    all_text = f"{criterion_text} {comment or ''} {recommendation or ''}"
    legal_refs = LEGAL_REF_RE.findall(all_text)
    legal_ref = "; ".join(legal_refs) if legal_refs else None

    needs_review = False
    if status is None:
        needs_review = True
    if len(criterion_text) < 20:
        needs_review = True

    return {
        "section": section,
        "criterion_text": criterion_text,
        "status": status,
        "comment": comment,
        "recommendation": recommendation,
        "legal_ref": legal_ref,
        "photo_refs": photo_str,
        "needs_review": needs_review,
        "_in_flagged": in_flagged,
    }


# ── Deduplication ──────────────────────────────────────────────────────────────

def deduplicate(observations: list[dict]) -> list[dict]:
    """Deduplicate by criterion_text. Keep instance with longest comment+rec."""
    seen: dict[str, dict] = {}
    for obs in observations:
        key = obs["criterion_text"].strip().lower()
        if key in seen:
            existing = seen[key]
            e_len = len(existing.get("comment") or "") + len(existing.get("recommendation") or "")
            n_len = len(obs.get("comment") or "") + len(obs.get("recommendation") or "")
            if n_len > e_len:
                seen[key] = obs
        else:
            seen[key] = obs
    return list(seen.values())


# ── Process PDF ────────────────────────────────────────────────────────────────

def process_pdf(pdf_path: str) -> dict:
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    pdf = pdfplumber.open(str(path))
    metadata = extract_metadata(pdf)
    raw_observations, skipped_blocks = parse_observations(pdf)

    for obs in raw_observations:
        obs["audit_date"] = metadata["audit_date"]
        obs["site_address"] = metadata["site_address"]
        obs["prepared_by"] = metadata["prepared_by"]
        obs["source_pdf"] = path.name
        del obs["_in_flagged"]

    deduped = deduplicate(raw_observations)

    ncr_count = sum(1 for o in deduped if o["status"] == "NCR")
    null_count = sum(1 for o in deduped if o["status"] is None)
    review_count = sum(1 for o in deduped if o["needs_review"])
    pdf.close()

    return {
        "observations": deduped,
        "summary": {
            "filename": path.name,
            "total": len(deduped),
            "ncr_count": ncr_count,
            "null_status_count": null_count,
            "needs_review_count": review_count,
            "skipped_advisory_blocks": skipped_blocks,
        },
    }


# ── Field mapping ──────────────────────────────────────────────────────────────

def map_to_db_row(obs: dict) -> dict:
    """Map extracted observation fields to pims_observations columns."""
    return {
        "audit_id": None,               # flat import — no FK
        "audit_date": obs["audit_date"],
        "site_address": obs["site_address"],
        "prepared_by": obs["prepared_by"],
        "ccvs_category": obs["section"],
        "observation_text": obs["criterion_text"],
        "conformance_status": obs["status"],
        "action_description": obs["comment"],
        "recommendation": obs["recommendation"],
        "legal_ref": obs["legal_ref"],
        "photo_refs": obs["photo_refs"],
        "source_pdf": obs["source_pdf"],
        "needs_review": obs["needs_review"],
        "staging": True,
    }


# ── Supabase insert ───────────────────────────────────────────────────────────

def upsert_observations(rows: list[dict], env_path: str) -> dict:
    """
    Upsert rows to pims_observations via Supabase REST API.
    Returns {"inserted": N, "errors": [(row, err), ...]}.
    """
    from dotenv import dotenv_values
    import requests

    env = dotenv_values(env_path)
    url = env.get("SUPABASE_URL")
    key = env.get("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        print("FATAL: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY missing from .env",
              file=sys.stderr)
        sys.exit(1)

    endpoint = f"{url.rstrip('/')}/rest/v1/pims_observations"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    inserted = 0
    errors: list[tuple[dict, str]] = []

    for row in rows:
        try:
            resp = requests.post(
                endpoint,
                headers=headers,
                json=row,
                timeout=30,
            )
            if resp.status_code in (200, 201):
                inserted += 1
            else:
                errors.append((row, f"HTTP {resp.status_code}: {resp.text[:200]}"))
        except Exception as e:
            errors.append((row, str(e)))

    return {"inserted": inserted, "errors": errors}


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Extract observations from RPD audit PDFs")
    parser.add_argument("--pdf", help="Path to a single PDF")
    parser.add_argument("--folder", help="Path to folder of PDFs")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Print JSON to stdout (default)")
    parser.add_argument("--insert", action="store_true",
                        help="Write to Supabase")
    parser.add_argument("--exclude", nargs="*", default=[],
                        help="Substrings to exclude from PDF filenames")
    args = parser.parse_args()

    if not args.pdf and not args.folder:
        parser.error("Provide --pdf or --folder")

    pdf_paths: list[str] = []
    if args.pdf:
        pdf_paths.append(args.pdf)
    if args.folder:
        folder = Path(args.folder)
        if not folder.is_dir():
            print(f"ERROR: Folder not found: {args.folder}", file=sys.stderr)
            sys.exit(1)
        for p in sorted(folder.glob("*.pdf")):
            if any(ex.lower() in p.name.lower() for ex in args.exclude):
                print(f"EXCLUDED (--exclude match): {p.name}")
                continue
            pdf_paths.append(str(p))

    env_path = str(Path(__file__).resolve().parents[2] / ".env")

    exit_code = 0
    all_db_rows: list[dict] = []

    for pdf_path in pdf_paths:
        try:
            result = process_pdf(pdf_path)
            s = result["summary"]

            if not args.insert:
                # Dry-run: print JSON + summary
                print(json.dumps(result["observations"], indent=2, default=str))
            else:
                # Insert mode: show mapped rows for transparency
                db_rows = [map_to_db_row(obs) for obs in result["observations"]]
                all_db_rows.extend(db_rows)
                print(json.dumps(db_rows, indent=2, default=str))

            print(
                f"\nExtracted {s['total']} observations from {s['filename']}. "
                f"NCR: {s['ncr_count']}. NULL-status: {s['null_status_count']}. "
                f"Needs-review: {s['needs_review_count']}."
            )
            if s["skipped_advisory_blocks"]:
                print("Skipped advisory blocks:")
                for blk in s["skipped_advisory_blocks"]:
                    print(f"  - {blk}")
        except Exception as e:
            print(f"ERROR processing {pdf_path}: {e}", file=sys.stderr)
            import traceback; traceback.print_exc()
            exit_code = 1

    # Insert mode: upsert all collected rows
    if args.insert and all_db_rows:
        print(f"\nUpserting {len(all_db_rows)} rows to pims_observations...")
        result = upsert_observations(all_db_rows, env_path)
        inserted = result["inserted"]
        errored = len(result["errors"])
        review_count = sum(1 for r in all_db_rows if r.get("needs_review"))
        print(
            f"Inserted {inserted}, skipped {errored} (errors), "
            f"flagged {review_count} for review."
        )
        if result["errors"]:
            for row, err in result["errors"]:
                print(f"  ERROR: {err}", file=sys.stderr)
                print(f"    ROW: {json.dumps(row, default=str)[:200]}", file=sys.stderr)
            if exit_code == 0:
                exit_code = 0  # Row errors don't change exit code per spec

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
