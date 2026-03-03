#!/usr/bin/env python3
"""
renderers/md_renderer.py — TaskBlock → Markdown string

render_md(task: TaskBlock) -> str

Output structure matches the spec exactly. If task.approved is False,
appends an AI-GENERATED warning blockquote.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.schema import TaskBlock


def render_md(task: TaskBlock) -> str:
    lines: list[str] = []

    # Title + scope
    lines.append(f"**{task.task}**")
    lines.append(f"*Scope: {task.scope}*")
    lines.append("")

    # Hold points
    lines.append("**HOLD POINT \u2014 do not start until:**")
    if task.hold_points:
        for item in task.hold_points:
            lines.append(f"- {item}")
    else:
        lines.append("- *(none)*")
    lines.append("")

    # Controls
    lines.append("**Controls:**")
    if task.controls:
        for item in task.controls:
            lines.append(f"- {item}")
    else:
        lines.append("- *(none)*")
    lines.append("")

    # Stop work
    lines.append("**STOP WORK if:**")
    if task.stop_work:
        for item in task.stop_work:
            lines.append(f"- {item}")
    else:
        lines.append("- *(none)*")
    lines.append("")

    # Admin
    lines.append("**Admin:**")
    if task.admin:
        for item in task.admin:
            lines.append(f"- {item}")
    else:
        lines.append("- *(none)*")
    lines.append("")

    # PPE
    lines.append("**PPE:**")
    if task.ppe:
        for item in task.ppe:
            lines.append(f"- {item}")
    else:
        lines.append("- *(none)*")
    lines.append("")

    # Responsibility
    lines.append("**Who checks:**")
    if task.responsibility:
        for role, obligation in task.responsibility.items():
            lines.append(f"- {role} \u2014 {obligation}")
    else:
        lines.append("- *(none)*")
    lines.append("")

    # Risk + CCVS
    lines.append(f"**Risk:** {task.risk_pre} \u2192 {task.risk_post}")
    lines.append(f"**CCVS:** {task.ccvs_code or 'N/A'}")

    # Unapproved warning
    if not task.approved:
        lines.append("")
        lines.append(
            "> \u26a0 AI-GENERATED \u2014 PENDING REVIEW. "
            "Do not issue until approved."
        )

    return "\n".join(lines)
