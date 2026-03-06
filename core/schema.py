from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime


class ResponsibilityEntry(BaseModel):
    role: Literal["SUP", "WKR", "SUB", "PM", "OP"]
    obligation: str


class MonitoringEntry(BaseModel):
    critical_control: str
    who: str
    frequency: Literal[
        "before each use",
        "each shift start",
        "continuous",
        "daily",
        "weekly"
    ]
    evidence: str


class TaskBlock(BaseModel):
    task: str
    scope: str
    risk_pre: str
    risk_post: str
    hold_points: list[str] = Field(default_factory=list)
    controls: list[str] = Field(default_factory=list)
    stop_work: list[str] = Field(default_factory=list)
    admin: list[str] = Field(default_factory=list)
    ppe: list[str] = Field(default_factory=list)
    responsibility: dict[str, str]
    ccvs_code: str | None = None
    monitoring: MonitoringEntry | None = None
    wah_applicable: bool = False
    source: Literal["library", "ai-generated"] = "library"
    approved: bool = False
    version: str = "1.0"
    db_id: int | None = None


class ValidationResult(BaseModel):
    passed: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    fog_scores: dict[str, float] = Field(default_factory=dict)
    word_counts: dict[str, int] = Field(default_factory=dict)

    def summary(self) -> str:
        lines = []
        lines.append(f"PASSED: {self.passed}")
        if self.errors:
            lines.append(f"ERRORS ({len(self.errors)}):")
            for e in self.errors:
                lines.append(f"  ✗ {e}")
        if self.warnings:
            lines.append(f"WARNINGS ({len(self.warnings)}):")
            for w in self.warnings:
                lines.append(f"  ⚠ {w}")
        if self.fog_scores:
            lines.append("FOG SCORES (per bullet):")
            for bullet, score in self.fog_scores.items():
                lines.append(f"  {score:.1f} — {bullet[:60]}")
        return "\n".join(lines)


class AuditEvent(BaseModel):
    event_type: str
    task_id: int | None = None
    user: str = "system"
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat()
    )
    inputs: str = ""
    output_hash: str = ""
    ai_unapproved: bool = False
