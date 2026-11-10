"""Compare two eval runs over the same questions and say whether the gain is real."""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from .stats import mcnemar_exact, paired_bootstrap


def load(path: str | Path) -> dict[str, dict]:
    """One JSON object per line: {"id": ..., "correct": true/false, "tag"?: ...}
    or {"id": ..., "pred": ..., "gold": ...} (correct = pred == gold)."""
    rows: dict[str, dict] = {}
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        r = json.loads(line)
        if "id" not in r:
            raise ValueError(f"{path}:{n}: missing 'id'")
        if "correct" not in r:
            if "pred" not in r or "gold" not in r:
                raise ValueError(f"{path}:{n}: need 'correct' or 'pred' + 'gold'")
            r["correct"] = str(r["pred"]).strip() == str(r["gold"]).strip()
        key = str(r["id"])
        if key in rows:
            raise ValueError(f"{path}:{n}: duplicate id {key!r}")
        rows[key] = r
    return rows


@dataclass
class Report:
    n: int
    acc_before: float
    acc_after: float
    gained: list[str]
    lost: list[str]
    p_value: float
    ci: tuple[float, float]
    verdict: str
    missing: list[str] = field(default_factory=list)
    slices: dict[str, tuple[int, int, int]] = field(default_factory=dict)  # tag -> (n, gained, lost)

    @property
    def delta(self) -> float:
        return self.acc_after - self.acc_before


def compare(before: dict[str, dict], after: dict[str, dict], *, alpha: float = 0.05,
            iters: int = 10_000, seed: int = 0) -> Report:
    ids = [i for i in before if i in after]  # keep file order
    if not ids:
        raise ValueError("the two runs share no question ids")
    # Questions in only one run are reported, never silently dropped:
    # a run that skipped hard questions would otherwise look better.
    missing = sorted(set(before) ^ set(after))

    b = [bool(before[i]["correct"]) for i in ids]
    a = [bool(after[i]["correct"]) for i in ids]
    gained = [i for i, x, y in zip(ids, b, a) if not x and y]
    lost = [i for i, x, y in zip(ids, b, a) if x and not y]

    p = mcnemar_exact(len(gained), len(lost))
    lo, hi = paired_bootstrap(b, a, iters=iters, seed=seed, level=1 - alpha)
    if p < alpha and lo > 0:
        verdict = "REAL GAIN"
    elif p < alpha and hi < 0:
        verdict = "REAL REGRESSION"
    else:
        verdict = "NOT PROVEN"

    slices: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    g, l = set(gained), set(lost)
    for i in ids:
        tag = str(after[i].get("tag", before[i].get("tag", "")))
        if not tag:
            continue
        s = slices[tag]
        s[0] += 1
        s[1] += i in g
        s[2] += i in l

    return Report(n=len(ids), acc_before=sum(b) / len(b), acc_after=sum(a) / len(a),
                  gained=gained, lost=lost, p_value=p, ci=(lo, hi), verdict=verdict,
                  missing=missing, slices={k: tuple(v) for k, v in sorted(slices.items())})


def render(r: Report) -> str:
    pct = lambda x: f"{x * 100:+.1f} pts" if x else "0.0 pts"
    out = [
        f"{r.verdict}",
        "",
        f"questions compared : {r.n}",
        f"accuracy           : {r.acc_before:.1%} -> {r.acc_after:.1%}  ({pct(r.delta)})",
        f"flips              : {len(r.gained)} wrong->right, {len(r.lost)} right->wrong",
        f"McNemar p-value    : {r.p_value:.4f}",
        f"95% CI of change   : [{pct(r.ci[0])}, {pct(r.ci[1])}]  (paired bootstrap)",
    ]
    if r.missing:
        out.append(f"WARNING            : {len(r.missing)} id(s) in only one run, excluded: {', '.join(r.missing[:5])}"
                   + (" ..." if len(r.missing) > 5 else ""))
    worse = [(t, s) for t, s in r.slices.items() if s[2] > s[1]]
    if r.slices:
        out += ["", "by tag (n, gained, lost):"]
        out += [f"  {t:<14} {s[0]:>4} {s[1]:>4} {s[2]:>4}" + ("   <- got worse" if (t, s) in worse else "")
                for t, s in r.slices.items()]
    if r.lost:
        out += ["", f"right->wrong ids (check these first): {', '.join(r.lost[:10])}" + (" ..." if len(r.lost) > 10 else "")]
    return "\n".join(out)
