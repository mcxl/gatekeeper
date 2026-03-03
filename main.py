#!/usr/bin/env python3
"""Gatekeeper CLI — python main.py {generate|approve|list|score|seed}"""

import argparse, io, os, sqlite3, subprocess, sys

# Ensure Unicode output works on Windows cp1252 consoles
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _ROOT)
DB_PATH = os.path.join(_ROOT, "db", "gatekeeper.db")
OUT_DIR = os.path.join(_ROOT, "src", "outputs")


def cmd_generate(args):
    from core.library import query_task
    from renderers.docx_renderer import render_docx
    from renderers.md_renderer import render_md
    task = query_task(args.task_name)
    os.makedirs(OUT_DIR, exist_ok=True)
    slug = args.task_name.replace(" ", "_").replace("/", "-")[:40]
    if args.output in ("docx", "both"):
        p = os.path.join(OUT_DIR, f"{slug}.docx")
        open(p, "wb").write(render_docx(task))
        print(f"DOCX: {p}")
    if args.output in ("md", "both"):
        p = os.path.join(OUT_DIR, f"{slug}.md")
        open(p, "w", encoding="utf-8").write(render_md(task))
        print(f"MD:   {p}")
    print(f"Source: {task.source}  Approved: {task.approved}")


def cmd_approve(args):
    from core.library import approve_task
    approve_task(args.task_id, args.user)
    print(f"Task {args.task_id} approved by {args.user}.")


def cmd_list(args):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    q = "SELECT id,task_name,status,source,version FROM Tasks"
    params = ()
    if args.status:
        q += " WHERE status=?"
        params = (args.status,)
    rows = conn.execute(q + " ORDER BY id", params).fetchall()
    conn.close()
    print(f"{'ID':<5} {'STATUS':<10} {'SRC':<12} {'VER':<5} TASK")
    print("-" * 80)
    for r in rows:
        print(f"{r['id']:<5} {r['status']:<10} {r['source']:<12} {r['version']:<5} {r['task_name'][:55]}")
    print(f"\n{len(rows)} task(s).")


def cmd_score(args):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM Tasks WHERE id=?", (args.task_id,)).fetchone()
    if not row:
        print(f"Task {args.task_id} not found."); sys.exit(1)
    from core.library import _load_task_from_row
    from core.validate import validate_task
    print(validate_task(_load_task_from_row(conn.cursor(), row)).summary())
    conn.close()


def cmd_seed(_):
    sys.exit(subprocess.run([sys.executable, os.path.join(_ROOT, "db", "seed.py")]).returncode)


def main():
    p = argparse.ArgumentParser(prog="gatekeeper")
    s = p.add_subparsers(dest="command", required=True)

    g = s.add_parser("generate"); g.add_argument("task_name")
    g.add_argument("--output", choices=["docx", "md", "both"], default="both")

    a = s.add_parser("approve"); a.add_argument("task_id", type=int)
    a.add_argument("--user", required=True)

    ls = s.add_parser("list")
    ls.add_argument("--status", choices=["approved", "draft", "archived"])

    sc = s.add_parser("score"); sc.add_argument("task_id", type=int)
    s.add_parser("seed")

    args = p.parse_args()
    {"generate": cmd_generate, "approve": cmd_approve,
     "list": cmd_list, "score": cmd_score, "seed": cmd_seed}[args.command](args)


if __name__ == "__main__":
    main()
