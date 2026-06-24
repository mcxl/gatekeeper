"""RulePackV1.1 validation and fail-closed loading."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

RULE_PACK_SCHEMA_VERSION = "1.1"
NON_PRODUCTION_ENVIRONMENTS = frozenset({"development", "test", "testing", "local"})

STATUS_AVAILABLE = "AVAILABLE"
STATUS_DRAFT = "DRAFT"
STATUS_INVALID = "INVALID"
STATUS_PACK_INACTIVE = "PACK_INACTIVE"
STATUS_UNAVAILABLE = "UNAVAILABLE"

_SCHEMA_PATH = Path(__file__).with_name("rule_pack_v1_1.json")


@dataclass(frozen=True)
class RulePackLoadResult:
    """Outcome of loading a project rule pack."""

    status: str
    should_evaluate: bool
    pack: dict[str, Any] = field(default_factory=dict)
    errors: tuple[str, ...] = ()


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    with _SCHEMA_PATH.open(encoding="utf-8") as schema_file:
        schema = json.load(schema_file)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _error_path(error) -> str:
    path = ".".join(str(part) for part in error.absolute_path)
    return path or "$"


def validate_rule_pack(pack: dict[str, Any]) -> list[str]:
    """Return deterministic validation errors for a RulePackV1.1 mapping."""

    if not isinstance(pack, dict):
        return ["$: rule pack must be a JSON object"]

    errors = [
        f"{_error_path(error)}: {error.message}"
        for error in _validator().iter_errors(pack)
    ]

    criterion_ids = [
        criterion.get("criterion_id")
        for criterion in pack.get("criteria", [])
        if isinstance(criterion, dict)
    ]
    duplicates = sorted({
        criterion_id
        for criterion_id in criterion_ids
        if criterion_id and criterion_ids.count(criterion_id) > 1
    })
    errors.extend(
        f"criteria: duplicate criterion_id '{criterion_id}'"
        for criterion_id in duplicates
    )
    return sorted(errors)


def _allow_draft_from_env() -> bool:
    return os.getenv("PROCORE_ALLOW_DRAFT_RULE_PACKS", "false").strip().lower() == "true"


def load_rule_pack(
    path: str | Path,
    *,
    environment: str | None = None,
    allow_draft: bool | None = None,
) -> RulePackLoadResult:
    """Load a pack and decide whether project criteria may be evaluated."""

    rule_pack_path = Path(path)
    if not rule_pack_path.is_file():
        return RulePackLoadResult(
            status=STATUS_UNAVAILABLE,
            should_evaluate=False,
        )

    try:
        with rule_pack_path.open(encoding="utf-8") as pack_file:
            pack = json.load(pack_file)
    except (OSError, json.JSONDecodeError) as exc:
        return RulePackLoadResult(
            status=STATUS_INVALID,
            should_evaluate=False,
            errors=(f"$: could not load rule pack: {exc}",),
        )

    errors = validate_rule_pack(pack)
    if errors:
        return RulePackLoadResult(
            status=STATUS_INVALID,
            should_evaluate=False,
            pack=pack,
            errors=tuple(errors),
        )

    status = pack["status"]
    if status == "active":
        return RulePackLoadResult(
            status=STATUS_AVAILABLE,
            should_evaluate=True,
            pack=pack,
        )

    if status == "draft":
        runtime_environment = (
            environment
            if environment is not None
            else os.getenv("ENVIRONMENT", "production")
        ).strip().lower()
        draft_enabled = allow_draft if allow_draft is not None else _allow_draft_from_env()
        if draft_enabled and runtime_environment in NON_PRODUCTION_ENVIRONMENTS:
            return RulePackLoadResult(
                status=STATUS_DRAFT,
                should_evaluate=True,
                pack=pack,
            )

    return RulePackLoadResult(
        status=STATUS_PACK_INACTIVE,
        should_evaluate=False,
        pack=pack,
    )
