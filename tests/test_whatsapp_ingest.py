from __future__ import annotations

import base64
import json
import zipfile
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from pims.services.whatsapp_ingest import (
    clean_whatsapp_filename,
    export_evidence_photos,
    ingest_zip,
    parse_chat,
    slug_audit_ref,
    to_observation_payload,
)


def _jpg_bytes(color=(200, 200, 200), size=(900, 1600)) -> bytes:
    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _make_zip(tmp_path: Path, chat: str, media: dict[str, bytes]) -> Path:
    zip_path = tmp_path / "WhatsApp Chat - Audit.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("_chat.txt", chat)
        for name, data in media.items():
            zf.writestr(name, data)
    return zip_path


def test_parse_sample_ios_shape_with_override_audit_ref(tmp_path):
    filename = "00000002-PHOTO-2026-05-19-12-29-08.jpg"
    chat = (
        "[19/5/2026, 12:26:58\u202fpm] Audit: \u200eYou created group “Audit”\n"
        "[19/5/2026, 12:26:58\u202fpm] Audit: \u200eMessages and calls are end-to-end encrypted. Only people in this chat can read, listen to, or share them.\n"
        f"\u200e[19/5/2026, 12:29:08\u202fpm] Alan richardson: Door frame \u200e<attached: {filename}>\n"
        "[20/5/2026, 1:05:44\u202fpm] Alan richardson: \u200eLocation: https://maps.google.com/?q=-33.703510,150.699585\n"
    )
    zip_path = _make_zip(tmp_path, chat, {filename: _jpg_bytes()})

    messages = parse_chat(zip_path, audit_ref="Audit-WAtest-2026-05-19")

    assert len(messages) == 1
    msg = messages[0]
    assert msg.timestamp.isoformat() == "2026-05-19T12:29:08+10:00"
    assert msg.author == "Alan richardson"
    assert msg.caption == "Door frame"
    assert msg.attachment_filename == filename
    assert msg.audit_ref == "Audit-WAtest-2026-05-19"

    prepared = to_observation_payload(msg, zip_path)
    payload = prepared.payload
    assert payload["observation_text"] == "Door frame"
    assert payload["submitted_by"] == "Alan richardson"
    assert payload["filename"] == "2026-05-19-12-29-08.jpg"
    assert payload["device_info"] == "whatsapp-export"
    assert payload["audit_ref"] == "Audit-WAtest-2026-05-19"
    assert len(payload["photo_base64"]) < 20_000_000
    assert base64.b64decode(payload["photo_base64"])


def test_audit_block_assigns_following_photos(tmp_path):
    filename = "00000003-PHOTO-2026-05-20-09-00-00.jpg"
    chat = (
        "[20/5/2026, 8:55:00 am] Alan: AUDIT: Audit - Cremorne - 2026-05-20\n"
        "[20/5/2026, 8:55:01 am] Alan: PROJECT_VALUE: gt_250k\n"
        "[20/5/2026, 8:55:02 am] Alan: SITE: Cremorne\n"
        f"[20/5/2026, 9:00:00 am] Alan: Open edge <attached: {filename}>\n"
    )
    zip_path = _make_zip(tmp_path, chat, {filename: _jpg_bytes()})

    [msg] = parse_chat(zip_path)

    assert msg.audit_ref == "Audit-Cremorne-2026-05-20"
    assert msg.project_value == "gt_250k"
    assert msg.site == "Cremorne"


def test_unknown_project_value_is_dropped(tmp_path):
    filename = "photo.jpg"
    chat = (
        "[20/5/2026, 8:55:00 am] Alan: AUDIT: Audit-Test-2026-05-20\n"
        "[20/5/2026, 8:55:01 am] Alan: PROJECT_VALUE: cheap\n"
        f"[20/5/2026, 9:00:00 am] Alan: Open edge <attached: {filename}>\n"
    )
    zip_path = _make_zip(tmp_path, chat, {filename: _jpg_bytes()})

    [msg] = parse_chat(zip_path)

    assert msg.project_value is None


def test_missing_audit_ref_rejected_when_building_payload(tmp_path):
    filename = "photo.jpg"
    chat = f"[20/5/2026, 9:00:00 am] Alan: Open edge <attached: {filename}>\n"
    zip_path = _make_zip(tmp_path, chat, {filename: _jpg_bytes()})

    [msg] = parse_chat(zip_path)

    with pytest.raises(ValueError, match="no audit_ref"):
        to_observation_payload(msg, zip_path)


def test_adjacent_text_caption_and_uncaptioned_fallback(tmp_path):
    filename_1 = "photo1.jpg"
    filename_2 = "photo2.jpg"
    chat = (
        "[20/5/2026, 9:00:00 am] Alan: AUDIT: Audit-Test-2026-05-20\n"
        "[20/5/2026, 9:00:10 am] Alan: Scaffold tag missing\n"
        f"[20/5/2026, 9:00:20 am] Alan: <attached: {filename_1}>\n"
        f"[20/5/2026, 9:05:20 am] Alan: <attached: {filename_2}>\n"
    )
    zip_path = _make_zip(tmp_path, chat, {
        filename_1: _jpg_bytes((255, 0, 0)),
        filename_2: _jpg_bytes((0, 255, 0)),
    })

    msgs = parse_chat(zip_path)
    assert msgs[0].caption == "Scaffold tag missing"
    assert msgs[1].caption is None
    assert to_observation_payload(msgs[1], zip_path).payload["observation_text"] == "Photo observation: photo2.jpg"


def test_dedupe_skips_repeated_import_and_renamed_same_photo(tmp_path):
    photo = _jpg_bytes()
    chat = (
        "[20/5/2026, 9:00:00 am] Alan: AUDIT: Audit-Test-2026-05-20\n"
        "[20/5/2026, 9:00:10 am] Alan: One <attached: a.jpg>\n"
        "[20/5/2026, 9:00:20 am] Alan: Two <attached: b.jpg>\n"
    )
    zip_path = _make_zip(tmp_path, chat, {"a.jpg": photo, "b.jpg": photo})
    log_path = tmp_path / "dedupe.jsonl"

    first = ingest_zip(zip_path, dedupe_log=log_path, dry_run=True)
    assert first.posted == 1
    first_payload = first.payloads[0]
    assert first_payload["filename"] == "a.jpg"

    # Dry-run does not mutate the log. Simulate the successful post record.
    prepared = to_observation_payload(parse_chat(zip_path)[0], zip_path)
    log_path.write_text(json.dumps({
        "audit_ref": first_payload["audit_ref"],
        "ts": prepared.message.timestamp.isoformat(),
        "filename": "a.jpg",
        "sha256": prepared.photo_sha256,
        "dedupe_key": prepared.dedupe_key,
        "observation_id": "obs-1",
    }) + "\n", encoding="utf-8")

    second = ingest_zip(zip_path, dedupe_log=log_path, dry_run=True)
    assert second.posted == 0
    assert second.skipped == 2


def test_ambiguous_attachment_basename_is_rejected(tmp_path):
    chat = (
        "[20/5/2026, 9:00:00 am] Alan: AUDIT: Audit-Test-2026-05-20\n"
        "[20/5/2026, 9:00:10 am] Alan: One <attached: photo.jpg>\n"
    )
    zip_path = _make_zip(tmp_path, chat, {
        "a/photo.jpg": _jpg_bytes((255, 0, 0)),
        "b/photo.jpg": _jpg_bytes((0, 255, 0)),
    })

    [msg] = parse_chat(zip_path)

    with pytest.raises(ValueError, match="ambiguous"):
        to_observation_payload(msg, zip_path)


def test_slug_audit_ref():
    assert slug_audit_ref("Audit - WAtest - 2026-05-19") == "Audit-WAtest-2026-05-19"


def test_clean_whatsapp_filename_strips_ios_photo_prefix():
    assert clean_whatsapp_filename("00000005-PHOTO-2026-05-20-22-04-52.jpg") == "2026-05-20-22-04-52.jpg"
    assert clean_whatsapp_filename("nested/00000005-PHOTO-2026-05-20-22-04-52.jpg") == "2026-05-20-22-04-52.jpg"
    assert clean_whatsapp_filename("site-photo.jpg") == "site-photo.jpg"


def test_export_evidence_photos_creates_dated_audit_folder_and_strips_prefix(tmp_path):
    filename = "00000005-PHOTO-2026-05-20-22-04-52.jpg"
    photo = _jpg_bytes()
    chat = (
        "[20/5/2026, 8:55:00 am] Alan: AUDIT: Audit-Test-2026-05-20\n"
        f"[20/5/2026, 9:00:10 am] Alan: One <attached: {filename}>\n"
    )
    zip_path = _make_zip(tmp_path, chat, {filename: photo})
    obs = to_observation_payload(parse_chat(zip_path)[0], zip_path)

    audit_folder = export_evidence_photos(zip_path, [obs], evidence_root=tmp_path / "SSA-evidence")

    assert audit_folder == tmp_path / "SSA-evidence" / "2026-05-20-RPD-01"
    photo_path = audit_folder / "2026-05-20-RPD-01-photos" / "2026-05-20-22-04-52.jpg"
    assert photo_path.read_bytes() == photo
    assert (audit_folder / ".whatsapp_audit_ref").read_text(encoding="utf-8").strip() == "Audit-Test-2026-05-20"


def test_export_evidence_photos_reuses_marked_folder_for_same_audit(tmp_path):
    filename = "00000005-PHOTO-2026-05-20-22-04-52.jpg"
    chat = (
        "[20/5/2026, 8:55:00 am] Alan: AUDIT: Audit-Test-2026-05-20\n"
        f"[20/5/2026, 9:00:10 am] Alan: One <attached: {filename}>\n"
    )
    zip_path = _make_zip(tmp_path, chat, {filename: _jpg_bytes()})
    obs = to_observation_payload(parse_chat(zip_path)[0], zip_path)
    root = tmp_path / "SSA-evidence"

    first = export_evidence_photos(zip_path, [obs], evidence_root=root)
    second = export_evidence_photos(zip_path, [obs], evidence_root=root)

    assert first == second == root / "2026-05-20-RPD-01"
    assert not (root / "2026-05-20-RPD-02").exists()
    photos = list((root / "2026-05-20-RPD-01" / "2026-05-20-RPD-01-photos").glob("*.jpg"))
    assert len(photos) == 1


def test_export_evidence_photos_adopts_single_existing_unmarked_folder(tmp_path):
    filename = "00000005-PHOTO-2026-05-20-22-04-52.jpg"
    chat = (
        "[20/5/2026, 8:55:00 am] Alan: AUDIT: Audit-Test-2026-05-20\n"
        f"[20/5/2026, 9:00:10 am] Alan: One <attached: {filename}>\n"
    )
    zip_path = _make_zip(tmp_path, chat, {filename: _jpg_bytes()})
    obs = to_observation_payload(parse_chat(zip_path)[0], zip_path)
    existing = tmp_path / "SSA-evidence" / "2026-05-20-RPD-01"
    existing.mkdir(parents=True)

    audit_folder = export_evidence_photos(zip_path, [obs], evidence_root=tmp_path / "SSA-evidence")

    assert audit_folder == existing
    assert (existing / ".whatsapp_audit_ref").exists()


def test_parse_chat_skips_banner_photos(tmp_path):
    """Banner/metadata photos (project-value declarations, address-only context
    shots) must not be ingested as findings — they have no observation content
    and silently produce empty/garbage enrichment."""
    f_banner_pv = "00000001-PHOTO-2026-05-22-07-21-47.jpg"
    f_banner_addr = "00000002-PHOTO-2026-05-22-15-40-10.jpg"
    f_real = "00000003-PHOTO-2026-05-22-08-19-00.jpg"
    chat = (
        "[22/5/2026, 7:20:00 am] Alan: AUDIT: Audit-Banner-Test-2026-05-22\n"
        # Banner #1: project-value declaration as caption
        f"[22/5/2026, 7:21:48 am] Alan: 135 West Street, Crows Nest project value greater than $250,000 <attached: {f_banner_pv}>\n"
        # Banner #2: address-only caption
        f"[22/5/2026, 7:22:00 am] Alan: 33 Linda St Hornsby <attached: {f_banner_addr}>\n"
        # Real finding with address embedded — must NOT be filtered
        f"[22/5/2026, 8:19:01 am] Alan: Petrol brought onto site no SDS available in Breadcrumb. <attached: {f_real}>\n"
    )
    zip_path = _make_zip(
        tmp_path,
        chat,
        {f_banner_pv: _jpg_bytes(), f_banner_addr: _jpg_bytes(), f_real: _jpg_bytes()},
    )
    msgs = parse_chat(zip_path)
    assert len(msgs) == 1
    assert msgs[0].attachment_filename == f_real
    assert "Petrol" in msgs[0].caption
