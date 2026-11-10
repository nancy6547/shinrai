"""shinrai compare BEFORE.jsonl AFTER.jsonl [--alpha 0.05] [--seed 0] [--json]

Exit code: 0 = real gain, 1 = not proven, 2 = real regression (for CI)."""
from __future__ import annotations

import argparse
import json
import sys

from .compare import compare, load, render


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="shinrai", description="Is this eval gain real?")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compare", help="compare two runs over the same questions")
    c.add_argument("before")
    c.add_argument("after")
    c.add_argument("--alpha", type=float, default=0.05)
    c.add_argument("--seed", type=int, default=0)
    c.add_argument("--iters", type=int, default=10_000)
    c.add_argument("--json", action="store_true", help="print the report as JSON")
    args = ap.parse_args(argv)

    r = compare(load(args.before), load(args.after), alpha=args.alpha, seed=args.seed, iters=args.iters)
    if args.json:
        d = r.__dict__ | {"delta": r.delta}
        print(json.dumps(d, indent=2))
    else:
        print(render(r))
    return {"REAL GAIN": 0, "NOT PROVEN": 1, "REAL REGRESSION": 2}[r.verdict]


if __name__ == "__main__":
    sys.exit(main())
