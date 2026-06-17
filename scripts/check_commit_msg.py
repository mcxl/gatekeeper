#!/usr/bin/env python3
"""commit-msg hook: enforce a Conventional Commits subject line.

Invoked by pre-commit at the ``commit-msg`` stage with the path to the
commit message file as the first argument. Rejects the commit when the
first non-comment line does not match ``type(scope)?: summary``.

Merge / revert / fixup / squash commits are exempt so normal git flows
(``git merge``, ``git revert``, autosquash) are never blocked.
"""
from __future__ import annotations

import re
import sys

PATTERN = re.compile(
    r"^(feat|fix|docs|test|chore|refactor|perf|ci|build|style|revert)"
    r"(\([a-z0-9._/\- ]+\))?!?: .+"
)
EXEMPT_PREFIXES = ("Merge ", "Revert ", "fixup!", "squash!")


def first_real_line(text: str) -> str:
    """Return the first non-blank, non-comment line of the message."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped
    return ""


def main() -> int:
    if len(sys.argv) < 2:
        return 0
    with open(sys.argv[1], encoding="utf-8") as handle:
        subject = first_real_line(handle.read())

    if not subject or subject.startswith(EXEMPT_PREFIXES):
        return 0
    if PATTERN.match(subject):
        return 0

    sys.stderr.write(
        "\nCommit message rejected - not Conventional Commits.\n"
        f"  got:   {subject!r}\n"
        "  want:  <type>(<scope>): <summary>\n"
        "  types: feat fix docs test chore refactor perf ci build style revert\n"
        "  e.g.:  fix(procore): fail-closed webhook auth\n\n"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
