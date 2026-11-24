from __future__ import annotations

import argparse
import sys

from .core import compare, profile_csv, render_markdown


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="csv-drift-check",
        description="Compare two CSV snapshots. Exit 1 if there are errors.")
    p.add_argument("old")
    p.add_argument("new")
    p.add_argument("--key", help="column that must be unique (for example an id)")
    p.add_argument("--null-jump", type=float, default=0.10)
    p.add_argument("--row-change", type=float, default=0.20)
    a = p.parse_args(argv)
    try:
        old = profile_csv(a.old, a.key)
        new = profile_csv(a.new, a.key)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    findings = compare(old, new, a.null_jump, a.row_change)
    sys.stdout.write(render_markdown(a.old, a.new, old, new, findings))
    return 1 if any(f.severity == "error" for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
