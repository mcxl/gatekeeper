"""Post-process a generated docx so byte output is reproducible across runs.

python-docx stamps `dcterms:created` and `dcterms:modified` in
`docProps/core.xml` with the current wall-clock time on save, and the
underlying zip writer encodes the host's local time into every entry's
file-mod-time field. Both inject non-determinism into otherwise identical
output.

This module rewrites the docx zip in place with:
- a fixed timestamp (derived from the audit date) on every zip entry,
- core.xml `created` / `modified` set to that same timestamp,
- entries sorted by filename so directory order is stable.
"""

from __future__ import annotations

import datetime as _dt
import re
import shutil
import tempfile
import zipfile
from pathlib import Path


_CORE_NS = "{http://purl.org/dc/terms/}"
_RE_CREATED = re.compile(
    r"(<dcterms:created[^>]*>)[^<]*(</dcterms:created>)",
    re.DOTALL,
)
_RE_MODIFIED = re.compile(
    r"(<dcterms:modified[^>]*>)[^<]*(</dcterms:modified>)",
    re.DOTALL,
)

# Strip optional w14 paragraph identifiers. docxcompose merges two documents
# without renumbering paraIds, leaving duplicates that Word flags as
# "unreadable content". They're regenerated on next save anyway, so stripping
# them entirely is the safe and minimal fix.
_RE_PARA_ID = re.compile(r'\s+w14:paraId="[^"]*"')
_RE_TEXT_ID = re.compile(r'\s+w14:textId="[^"]*"')

# Self-closing custom styles with no <w:name> trigger Word's "Show Repairs"
# dialog. docxcompose pulls these in when the source doc has unnamed quick
# styles (Alan-Richardson.docx ships with a `<w:style w:styleId="a"/>` stub).
# Injecting a `<w:name>` keyed off the styleId keeps Word silent and never
# clobbers existing names.
_RE_STYLE_SELF_CLOSING = re.compile(
    r'<w:style\b([^>]*?)\bw:styleId="([^"]+)"([^>]*?)/>'
)
_RE_STYLE_OPEN_NO_NAME = re.compile(
    r'(<w:style\b[^>]*?\bw:styleId="([^"]+)"[^>]*?>)(?!.*?<w:name\b)',
    re.DOTALL,
)


def _patch_core_xml(content: bytes, iso_timestamp: str) -> bytes:
    text = content.decode("utf-8")
    text = _RE_CREATED.sub(rf"\g<1>{iso_timestamp}\g<2>", text)
    text = _RE_MODIFIED.sub(rf"\g<1>{iso_timestamp}\g<2>", text)
    return text.encode("utf-8")


def _strip_paraids(content: bytes) -> bytes:
    text = content.decode("utf-8")
    text = _RE_PARA_ID.sub("", text)
    text = _RE_TEXT_ID.sub("", text)
    return text.encode("utf-8")


def _ensure_styles_have_names(content: bytes) -> bytes:
    """Expand any self-closing or empty `<w:style>` that lacks a `<w:name>`.

    Word's "Show Repairs" dialog fires for any custom style missing its name.
    Inject `<w:name w:val="<styleId>"/>` and rewrite the element as open/close.
    """
    text = content.decode("utf-8")

    # Pass 1: self-closing styles -> expand to open/close with injected w:name.
    def _self_closing_fix(m: re.Match) -> str:
        before_id, style_id, after_id = m.group(1), m.group(2), m.group(3)
        return (
            f'<w:style{before_id} w:styleId="{style_id}"{after_id}>'
            f'<w:name w:val="{style_id}"/>'
            f'</w:style>'
        )

    text = _RE_STYLE_SELF_CLOSING.sub(_self_closing_fix, text)

    # Pass 2: open <w:style>... blocks that contain no <w:name> inside their
    # body. Cheaper to walk each style block individually with the stdlib than
    # to write a single recursive regex.
    def _open_fix(text_in: str) -> str:
        out: list[str] = []
        cursor = 0
        for m in re.finditer(r'<w:style\b[^/>]*?>', text_in):
            # Find the matching </w:style>
            end_m = re.search(r'</w:style>', text_in[m.end():])
            if not end_m:
                continue
            block_start = m.start()
            block_end = m.end() + end_m.end()
            block = text_in[block_start:block_end]
            if '<w:name' in block:
                continue  # already has a name, skip
            sid_m = re.search(r'w:styleId="([^"]+)"', block[: m.end() - m.start()])
            if not sid_m:
                continue
            sid = sid_m.group(1)
            fixed_block = block.replace(
                m.group(0),
                m.group(0) + f'<w:name w:val="{sid}"/>',
                1,
            )
            # Substitute back into text_in. Build incrementally:
            out.append(text_in[cursor:block_start])
            out.append(fixed_block)
            cursor = block_end
        out.append(text_in[cursor:])
        return "".join(out)

    text = _open_fix(text)
    return text.encode("utf-8")


def _is_word_part_xml(name: str) -> bool:
    """Word body / header / footer / endnote XML parts that carry paraIds."""
    if not name.startswith("word/"):
        return False
    if not name.endswith(".xml"):
        return False
    base = name[len("word/"):]
    return (
        base == "document.xml"
        or base.startswith("header") and base.endswith(".xml")
        or base.startswith("footer") and base.endswith(".xml")
        or base == "endnotes.xml"
        or base == "footnotes.xml"
        or base == "comments.xml"
    )


def make_docx_deterministic(docx_path: Path, audit_date: _dt.date) -> None:
    """Rewrite `docx_path` in place so two runs over the same inputs produce
    byte-identical files.

    `audit_date` seeds the timestamp written into every zip entry and into
    `docProps/core.xml`. Using the audit date (not a hard-coded epoch) means
    a build refresh after re-running humanise — which legitimately changes
    content — still produces a stable file for that input set.
    """
    iso = f"{audit_date.isoformat()}T00:00:00Z"
    zip_date = (audit_date.year, audit_date.month, audit_date.day, 0, 0, 0)

    with zipfile.ZipFile(docx_path, "r") as zin:
        names = sorted(zin.namelist())
        entries: list[tuple[zipfile.ZipInfo, bytes]] = []
        for name in names:
            data = zin.read(name)
            if name == "docProps/core.xml":
                data = _patch_core_xml(data, iso)
            if _is_word_part_xml(name):
                data = _strip_paraids(data)
            if name == "word/styles.xml":
                data = _ensure_styles_have_names(data)
            info = zipfile.ZipInfo(filename=name, date_time=zip_date)
            # Preserve compression mode for the entry.
            original_info = zin.getinfo(name)
            info.compress_type = original_info.compress_type
            info.external_attr = original_info.external_attr
            entries.append((info, data))

    # Write to a temp file then atomically replace.
    tmp_fd, tmp_path_str = tempfile.mkstemp(prefix="ssa-det-", suffix=".docx")
    tmp_path = Path(tmp_path_str)
    try:
        with zipfile.ZipFile(tmp_path, "w") as zout:
            for info, data in entries:
                zout.writestr(info, data)
        # zipfile keeps the FD open until context exits; close fd we got from mkstemp.
        import os
        os.close(tmp_fd)
        shutil.move(str(tmp_path), str(docx_path))
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
