"""The two statistics Shinrai uses. Standard library only.

Both work on PAIRED results: the same test questions, scored before and after
a change (a fine-tune, a new prompt, a new model). Pairing matters: a question
both versions get right tells you nothing about the change, so only the
questions that FLIPPED carry information.
"""
from __future__ import annotations

import random
from math import comb


def mcnemar_exact(gained: int, lost: int) -> float:
    """Two-sided exact McNemar test.

    gained = questions wrong before, right after
    lost   = questions right before, wrong after

    If the change did nothing, every flip is a coin toss, so `gained` follows
    Binomial(n = gained + lost, p = 0.5). The p-value is the chance of a split
    at least this lopsided by luck alone.
    """
    n = gained + lost
    if n == 0:
        return 1.0
    k = min(gained, lost)
    tail = sum(comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * tail)


def paired_bootstrap(before: list[bool], after: list[bool], *, iters: int = 10_000,
                     seed: int = 0, level: float = 0.95) -> tuple[float, float]:
    """Confidence interval for (accuracy after - accuracy before).

    Resample QUESTIONS with replacement, keeping each question's before/after
    pair together, and recompute the difference each time. The middle `level`
    share of those differences is the interval. Seeded, so it is repeatable.
    """
    if len(before) != len(after) or not before:
        raise ValueError("need two equal-length, non-empty lists")
    n = len(before)
    diffs_per_q = [int(a) - int(b) for b, a in zip(before, after)]
    rng = random.Random(seed)
    deltas = []
    for _ in range(iters):
        s = 0
        for _ in range(n):
            s += diffs_per_q[rng.randrange(n)]
        deltas.append(s / n)
    deltas.sort()
    lo = deltas[int((1 - level) / 2 * iters)]
    hi = deltas[min(iters - 1, int((1 + level) / 2 * iters))]
    return lo, hi
