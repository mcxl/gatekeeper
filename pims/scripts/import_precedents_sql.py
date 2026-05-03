"""Generate SQL UPSERT statements for precedent import (no env vars needed).

Used to bootstrap the corpus when RPD service-key env vars are not present
in the local shell. Writes one giant INSERT ... ON CONFLICT DO UPDATE to
a target file (or stdout) which can then be fed through Supabase MCP
execute_sql in chunks.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure repo root is on the path so `pims.services.precedent_importer` works.
_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from pims.services.precedent_importer import (  # noqa: E402
    discover_files,
    parse_report,
    ImportItem,
)


def _q(v) -> str:
    if v is None:
        return "NULL"
    s = str(v).replace("'", "''")
    return f"'{s}'"


def to_values(it: ImportItem) -> str:
    # If we have BOTH finding_text and recommendation_text, the
    # observation_text field would just duplicate them concatenated —
    # collapse to NULL on the wire to keep the bulk SQL size manageable.
    obs = it.observation_text
    if it.finding_text and it.recommendation_text and obs:
        obs = None
    return (
        "("
        f"{_q(it.source_kind)}, "
        f"{_q(it.source_file)}, "
        f"{_q(it.source_item_key)}, "
        f"{_q(it.source_hash)}, "
        f"{_q(it.finding_text)}, "
        f"{_q(it.recommendation_text)}, "
        f"{_q(obs)}, "
        f"{_q(it.normalized_key)}, "
        f"{_q(it.section_name)}, "
        f"{_q(it.status_normalized)}"
        ")"
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True)
    p.add_argument("--out", required=True, help="Output SQL file")
    p.add_argument("--chunk-size", type=int, default=40,
                   help="Number of rows per INSERT statement")
    args = p.parse_args()

    folder = Path(args.source)
    files = discover_files(folder)
    items: list[ImportItem] = []
    for f in files:
        items.extend(parse_report(f))

    cols = (
        "source_kind, source_file, source_item_key, source_hash, "
        "finding_text, recommendation_text, observation_text, normalized_key, "
        "section_name, status_normalized"
    )

    out_path = Path(args.out)
    with out_path.open("w", encoding="utf-8") as f:
        f.write(f"-- {len(items)} precedent items from {len(files)} reports\n")
        for i in range(0, len(items), args.chunk_size):
            chunk = items[i:i + args.chunk_size]
            values_sql = ",\n  ".join(to_values(it) for it in chunk)
            f.write(
                f"INSERT INTO public.pims_precedent_examples ({cols}) VALUES\n  "
                f"{values_sql}\n"
                "ON CONFLICT (source_kind, source_file, source_item_key) DO UPDATE SET\n"
                "  source_hash = EXCLUDED.source_hash,\n"
                "  finding_text = EXCLUDED.finding_text,\n"
                "  recommendation_text = EXCLUDED.recommendation_text,\n"
                "  observation_text = EXCLUDED.observation_text,\n"
                "  normalized_key = EXCLUDED.normalized_key,\n"
                "  section_name = EXCLUDED.section_name,\n"
                "  status_normalized = EXCLUDED.status_normalized;\n"
            )
    print(f"Wrote {len(items)} items in {(len(items) + args.chunk_size - 1) // args.chunk_size} statements to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
