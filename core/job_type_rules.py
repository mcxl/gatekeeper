"""
core/job_type_rules.py — Job-type rule packs for SWMS validation.

Provides mandatory task sequences, immediate-fail checks, and dominant
control family expectations for each recognised job_type.

CLT/crane and EWP sub-patterns are detected from task text, not from
job_type overloading. They apply additional checks on top of the base
job_type rule pack.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class JobTypeRulePack:
    job_type: str
    mandatory_task_sequence: list[str] = field(default_factory=list)
    immediate_fail_if_missing: list[str] = field(default_factory=list)
    dominant_control_families: dict[str, str] = field(default_factory=dict)
    mandatory_hrcw_triggers: list[str] = field(default_factory=list)
    mandatory_additional_controls: list[str] = field(default_factory=list)
    clt_crane_detected: bool = False


# ── Rule packs ───────────────────────────────────────────────────────────────

_REMEDIAL = JobTypeRulePack(
    job_type="remedial",
    mandatory_task_sequence=[
        "site_establishment_occupied_interface",
        "access_equipment_setup",
        "protection_exclusion_resident_interface",
        "removal_demolition_stripout",
        "substrate_prep_inspection_defect_exposure",
        "structural_defect_repairs",
        "waterproofing_sealant_flashing",
        "screed_tile_finish_reinstatement",
        "coatings_final_finish",
        "final_inspection_defect_closeout",
        "demobilisation",
    ],
    immediate_fail_if_missing=[
        "removal_demolition before waterproofing",
        "substrate_hold_point before membrane or tile reinstatement",
        "occupied_site_interface as framework control",
        "correct dominant control family in CCVS for demolition and chemistry tasks",
    ],
    dominant_control_families={
        "demolition": "SIL",
        "removal": "SIL",
        "waterproofing": "CHM",
        "membrane": "CHM",
        "coating": "CHM",
        "painting": "CHM",
        "tiling": "SIL",
    },
)

_NEW_BUILD = JobTypeRulePack(
    job_type="new_build",
    mandatory_task_sequence=[
        "site_establishment",
        "access_equipment_setup",
        "structural_works",
        "services_rough_in",
        "finishes",
        "defect_closeout",
        "demobilisation",
    ],
    immediate_fail_if_missing=[
        "structural sequence before finishes",
    ],
)

_DEMOLITION = JobTypeRulePack(
    job_type="demolition",
    mandatory_task_sequence=[
        "site_establishment",
        "services_isolation",
        "hazmat_survey_removal",
        "structural_demolition",
        "debris_removal",
        "demobilisation",
    ],
    immediate_fail_if_missing=[
        "services isolation before demolition",
        "hazmat survey before structural demolition",
    ],
)

_MAINTENANCE = JobTypeRulePack(
    job_type="maintenance",
    mandatory_task_sequence=[
        "site_establishment",
        "isolation_lockout",
        "maintenance_works",
        "testing_recommission",
        "demobilisation",
    ],
    immediate_fail_if_missing=[
        "isolation before maintenance works",
    ],
)


JOB_TYPE_RULES: dict[str, JobTypeRulePack] = {
    "remedial": _REMEDIAL,
    "new_build": _NEW_BUILD,
    "demolition": _DEMOLITION,
    "maintenance": _MAINTENANCE,
}


def get_rule_pack(job_type: str) -> Optional[JobTypeRulePack]:
    """Returns None silently if job_type is unrecognised or empty."""
    if not job_type:
        return None
    return JOB_TYPE_RULES.get(job_type)


# ── Sub-pattern detection (CLT/crane, EWP) ───────────────────────────────────

_CLT_CRANE_KEYWORDS = ("clt", "cross laminated timber", "panel lift",
                        "tower crane", "crane erection")

_EWP_ROOF_KEYWORDS = ("ewp", "elevated work platform", "boom lift", "scissor lift")
_EWP_ROOF_CONTEXT = ("roof", "facade", "gutter", "flashing")


def detect_clt_crane(tasks: list[dict]) -> bool:
    """Detect CLT/crane sub-pattern from task text."""
    all_text = " ".join(
        (t.get("task", "") + " " + t.get("scope", "")).lower() for t in tasks
    )
    return any(kw in all_text for kw in _CLT_CRANE_KEYWORDS)


def detect_ewp_roof(tasks: list[dict]) -> bool:
    """Detect EWP roof access sub-pattern from task text."""
    all_text = " ".join(
        (t.get("task", "") + " " + t.get("scope", "")).lower() for t in tasks
    )
    has_ewp = any(kw in all_text for kw in _EWP_ROOF_KEYWORDS)
    has_context = any(kw in all_text for kw in _EWP_ROOF_CONTEXT)
    return has_ewp and has_context


CLT_CRANE_IMMEDIATE_FAIL = [
    "engineer_led_erection_sequence",
    "crane_lift_setup_and_exclusion",
    "temporary_bracing_prop_discipline",
    "permanent_connection_before_release_logic",
]

EWP_ROOF_IMMEDIATE_FAIL = [
    "plant_setup_and_inspection_before_use",
    "transfer_method_named_explicitly",
    "rescue_plan_referenced",
]

OCCUPIED_RESIDENTIAL_ADDITIONAL = [
    "occupied_site_interface_as_standalone_framework_control",
    "resident_exclusion_zone_logic",
    "emergency_arrangements_for_occupied_building",
]
