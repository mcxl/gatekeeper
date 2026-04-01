#!/usr/bin/env python3
"""
scripts/make_prompt.py — Generate paste-ready prompts from templates + job briefs.

Usage:
    python scripts/make_prompt.py --template next_pilot_job --brief job_briefs/urban_flow_plumbing.json
    python scripts/make_prompt.py --list
    python scripts/make_prompt.py --template next_pilot_job --brief job_briefs/urban_flow_plumbing.json --dry-run
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT / "prompts" / "session_templates"
PARTIALS_DIR = ROOT / "prompts" / "partials"
BRIEFS_DIR = ROOT / "job_briefs"


def list_assets() -> str:
    """List available templates and briefs."""
    lines = ["Templates:"]
    for f in sorted(TEMPLATES_DIR.glob("*.md")):
        lines.append(f"  {f.stem}")
    lines.append("")
    lines.append("Partials:")
    for f in sorted(PARTIALS_DIR.glob("_*.md")):
        lines.append(f"  {f.stem}")
    lines.append("")
    lines.append("Job briefs:")
    for f in sorted(BRIEFS_DIR.glob("*.json")):
        with open(f, encoding="utf-8") as fh:
            data = json.load(fh)
        customer = data.get("customer", "?")
        job_type = data.get("job_type", "?")
        runs = data.get("jobs_run", 0)
        lines.append(f"  {f.name}  ({customer}, {job_type}, {runs} runs)")
    return "\n".join(lines)


def load_partial(name: str) -> str:
    """Load a partial file by name (without leading underscore or .md)."""
    clean = name.lstrip("_")
    path = PARTIALS_DIR / f"_{clean}.md"
    if not path.exists():
        raise FileNotFoundError(f"Partial not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def resolve_partials(text: str) -> str:
    """Replace {{>partial_name}} with partial file content."""
    pattern = re.compile(r"\{\{>(\w+)\}\}")
    def replacer(m):
        return load_partial(m.group(1))
    # Resolve up to 3 levels of nesting
    for _ in range(3):
        new_text = pattern.sub(replacer, text)
        if new_text == text:
            break
        text = new_text
    return text


def format_field(key: str, value) -> str:
    """Format a field value for template insertion."""
    if isinstance(value, list):
        if key == "scope_modifiers":
            return ", ".join(value)
        if key == "quick_scan_focus":
            return "\n".join(f"   - {item}" for item in value)
        if key == "batch_jobs":
            return "\n".join(f"- {item}" for item in value)
        return ", ".join(str(v) for v in value)
    if value is None:
        return ""
    return str(value)


def find_placeholders(text: str) -> list[str]:
    """Find all {{field}} placeholders (not partials)."""
    return re.findall(r"\{\{(?!>)(\w+)\}\}", text)


def render(template_name: str, brief_path: str, dry_run: bool = False) -> str:
    """Render a template with a job brief."""
    # Load template
    tpl_path = TEMPLATES_DIR / f"{template_name}.md"
    if not tpl_path.exists():
        raise FileNotFoundError(f"Template not found: {tpl_path}")
    template = tpl_path.read_text(encoding="utf-8")

    # Resolve partials first
    template = resolve_partials(template)

    # Load brief
    brief_file = Path(brief_path)
    if not brief_file.is_absolute():
        brief_file = ROOT / brief_file
    if not brief_file.exists():
        raise FileNotFoundError(f"Brief not found: {brief_file}")
    with open(brief_file, encoding="utf-8") as f:
        brief = json.load(f)

    # Find all placeholders
    placeholders = find_placeholders(template)
    unique = list(dict.fromkeys(placeholders))

    if dry_run:
        lines = [f"Template: {template_name}", f"Brief: {brief_file.name}", ""]
        for ph in unique:
            present = ph in brief and brief[ph] is not None
            val_preview = ""
            if present:
                raw = brief[ph]
                formatted = format_field(ph, raw)
                val_preview = f" = {formatted[:60]}{'...' if len(formatted) > 60 else ''}"
            status = "OK" if present else "MISSING"
            lines.append(f"  [{status}] {{{{{ph}}}}}{val_preview}")
        missing = [ph for ph in unique if ph not in brief or brief[ph] is None]
        if missing:
            lines.append(f"\n{len(missing)} missing field(s) — render would fail.")
        else:
            lines.append(f"\nAll {len(unique)} field(s) present — ready to render.")
        return "\n".join(lines)

    # Check for missing required fields
    missing = [ph for ph in unique if ph not in brief or brief[ph] is None]
    if missing:
        raise ValueError(f"Missing required fields in brief: {', '.join(missing)}")

    # Replace placeholders
    result = template
    for ph in unique:
        formatted = format_field(ph, brief[ph])
        result = result.replace(f"{{{{{ph}}}}}", formatted)

    # Update brief metadata
    brief["last_used"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    brief["jobs_run"] = brief.get("jobs_run", 0) + 1
    with open(brief_file, "w", encoding="utf-8") as f:
        json.dump(brief, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Generate paste-ready prompts from templates + job briefs."
    )
    parser.add_argument("--template", "-t", help="Template name (without .md)")
    parser.add_argument("--brief", "-b", help="Path to job brief JSON")
    parser.add_argument("--list", "-l", action="store_true", help="List templates and briefs")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Show field status without rendering")
    args = parser.parse_args()

    if args.list:
        print(list_assets())
        return

    if not args.template or not args.brief:
        parser.error("--template and --brief are required (or use --list)")

    try:
        output = render(args.template, args.brief, dry_run=args.dry_run)
        print(output)
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
