"""Parse a project-specific Risk Assessment docx into structured data.

The RA carries the project's WHS contract: which controls must be in
place at which phase, which activities are HRCW, which Hold Points
gate construction. The SSA audit is reviewed against the RA, so
findings that reference RA activity refs (``TP-05``) and hold points
(``HP-04``) sit closer to the document the principal contractor is
held to.

Authoritative shape (from
``Unitas_Risk_Assessment_all.docx`` and equivalent RA exports from
the gatekeeper RA generator):

  - project metadata table (2 cols, key/value rows: Project, Site
    address, Principal Contractor, …)
  - hold-point schedule (6 cols: HP code, description, package,
    condition to be met, sign-off authority, evidence required)
  - risk register (7 cols: Ref, Activity / Hazard, HRCW Category,
    Initial Risk, Controls, Residual Risk, Responsible / SWMS / HP).
    Phase headers appear as repeated-cell rows (every cell carries
    the phase name).

Non-conforming RAs (cell counts off, header text different) are
parsed best-effort — missing fields land as empty strings. The
parser never raises on a malformed input; the orchestrator decides
whether to enrich without RA context or skip the project-context
injection.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RAHoldPoint:
    code: str        # "HP-04"
    description: str
    package: str
    condition: str
    sign_off: str
    evidence: str


@dataclass(frozen=True)
class RAActivity:
    ref: str          # "TP-05"
    phase: str        # "6 – Tilt-Up Panel Erection"
    activity: str
    hrcw: str
    initial_risk: str
    controls: str
    residual_risk: str
    responsible: str


@dataclass
class RiskAssessment:
    project_name: str = ""
    site_address: str = ""
    principal_contractor: str = ""
    hold_points: list[RAHoldPoint] = field(default_factory=list)
    activities: list[RAActivity] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not (self.hold_points or self.activities)


_HP_REF_RE = re.compile(r"^HP-\d{2}$")
# Activity refs in the canonical RA: 2-letter package + dash + digits,
# optionally suffixed (TP-01A, MR-02). Phase header rows have phase-
# title text in the ref cell instead, which fails this match.
_ACTIVITY_REF_RE = re.compile(r"^[A-Z]{2}-\d{1,3}[A-Z]?$")
# Phase header rows look like "6 — Tilt-Up Panel Erection" — leading
# digit then em-dash / en-dash / hyphen then title.
_PHASE_HEADER_RE = re.compile(r"^\s*(\d{1,2})\s*[—–-]\s*(.+)$")


def _norm_cell(text: object) -> str:
    if text is None:
        return ""
    s = str(text).replace("\n", " ").strip()
    return re.sub(r"\s+", " ", s)


def _looks_like_phase_header(row_cells: list[str]) -> str:
    """Phase header rows repeat the same value across every cell.

    Returns the normalised phase title (e.g. ``"6 – Tilt-Up Panel
    Erection"``) when detected, else ``""``.
    """
    if not row_cells:
        return ""
    first = row_cells[0]
    if not first:
        return ""
    # Every non-empty cell on the row carries the same value.
    distinct = {c for c in row_cells if c}
    if len(distinct) != 1:
        return ""
    if not _PHASE_HEADER_RE.match(first):
        return ""
    return first


def _parse_metadata_table(table) -> tuple[str, str, str]:
    """Extract project / site / principal contractor from a 2-col table."""
    project = site = pc = ""
    for row in table.rows:
        if len(row.cells) < 2:
            continue
        key = _norm_cell(row.cells[0].text).lower()
        val = _norm_cell(row.cells[1].text)
        if not val:
            continue
        if "project" in key and not project:
            project = val
        elif "site address" in key:
            site = val
        elif "principal contractor" in key:
            pc = val
    return project, site, pc


def _parse_hold_points_table(table) -> list[RAHoldPoint]:
    out: list[RAHoldPoint] = []
    for row in table.rows:
        cells = [_norm_cell(c.text) for c in row.cells]
        if len(cells) < 6:
            continue
        ref = cells[0]
        if not _HP_REF_RE.match(ref):
            continue  # header row or stray
        out.append(RAHoldPoint(
            code=ref, description=cells[1], package=cells[2],
            condition=cells[3], sign_off=cells[4], evidence=cells[5],
        ))
    return out


def _parse_register_table(table) -> list[RAActivity]:
    out: list[RAActivity] = []
    current_phase = ""
    for row in table.rows:
        cells = [_norm_cell(c.text) for c in row.cells]
        if len(cells) < 7:
            continue
        # Phase header row?
        ph = _looks_like_phase_header(cells)
        if ph:
            current_phase = ph
            continue
        ref = cells[0]
        if not _ACTIVITY_REF_RE.match(ref):
            continue
        out.append(RAActivity(
            ref=ref,
            phase=current_phase,
            activity=cells[1],
            hrcw=cells[2],
            initial_risk=cells[3],
            controls=cells[4],
            residual_risk=cells[5],
            responsible=cells[6],
        ))
    return out


def parse_risk_assessment(path: Path) -> RiskAssessment:
    """Best-effort parse of a project RA docx.

    Selects tables by shape: ``2 cols`` → project metadata,
    ``6 cols`` with HP-XX refs → hold-point schedule, ``7 cols`` with
    activity refs → risk register. Multiple matching tables are
    processed in order; values from earlier tables don't overwrite.
    Returns an empty ``RiskAssessment`` if the docx is unreadable.
    """
    try:
        from docx import Document
    except Exception:
        log.warning("python-docx not available; RA parse skipped")
        return RiskAssessment()

    if not path.exists():
        return RiskAssessment()

    try:
        doc = Document(path)
    except Exception:
        log.warning("RA docx unreadable: %s", path, exc_info=True)
        return RiskAssessment()

    ra = RiskAssessment()
    for tbl in doc.tables:
        cols = len(tbl.columns)
        if cols == 2 and not ra.project_name:
            project, site, pc = _parse_metadata_table(tbl)
            ra.project_name = project
            ra.site_address = site
            ra.principal_contractor = pc
        elif cols == 6 and not ra.hold_points:
            ra.hold_points = _parse_hold_points_table(tbl)
        elif cols == 7 and not ra.activities:
            ra.activities = _parse_register_table(tbl)
    return ra


def autodiscover_in_folder(folder: Path) -> Path | None:
    """Find a Risk Assessment docx inside the audit folder.

    Match by filename: any ``*.docx`` with ``risk assessment`` (any
    case) in the name AND not already a watcher-owned artifact (no
    ``Site-Safety-Audit-Report-`` prefix). First match wins.
    """
    if not folder.is_dir():
        return None
    candidates = []
    for p in folder.iterdir():
        if not p.is_file() or p.suffix.lower() != ".docx":
            continue
        if p.name.startswith("Site-Safety-Audit-Report-"):
            continue
        if "risk assessment" in p.stem.lower().replace("_", " "):
            candidates.append(p)
    return sorted(candidates)[0] if candidates else None


def compact_context_block(ra: RiskAssessment, max_activities: int = 60) -> str:
    """Compact text representation for the vision prompt.

    Trims to ``max_activities`` rows (keeps within prompt-token
    budget). Activities list is grouped by phase to keep the model's
    attention on phase boundaries.
    """
    if ra.is_empty:
        return ""
    lines: list[str] = []
    lines.append("PROJECT RISK ASSESSMENT CONTEXT")
    if ra.project_name:
        lines.append(f"Project: {ra.project_name}")
    if ra.site_address:
        lines.append(f"Site: {ra.site_address}")
    if ra.principal_contractor:
        lines.append(f"Principal Contractor: {ra.principal_contractor}")

    if ra.hold_points:
        lines.append("")
        lines.append("HOLD POINTS:")
        for hp in ra.hold_points:
            lines.append(f"  {hp.code}  {hp.description} | {hp.package}")

    if ra.activities:
        lines.append("")
        lines.append("PHASES + ACTIVITIES:")
        seen_phase = ""
        emitted = 0
        for act in ra.activities:
            if emitted >= max_activities:
                lines.append(
                    f"  ... ({len(ra.activities) - emitted} more activities)"
                )
                break
            if act.phase != seen_phase:
                lines.append(f"[{act.phase}]")
                seen_phase = act.phase
            init = act.initial_risk or "-"
            resid = act.residual_risk or "-"
            hrcw = act.hrcw or "-"
            lines.append(
                f"  {act.ref}  {act.activity[:90]} | hrcw={hrcw} | "
                f"init={init} resid={resid}"
            )
            emitted += 1

    return "\n".join(lines)
