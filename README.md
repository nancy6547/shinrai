# Shinrai

**Is this eval gain real?** Compare two runs of the same test set (before and after a fine-tune, a prompt change or a new model) and get a verdict you can defend.

Shinrai (信頼) means "trust".

A model goes from 144 to 151 correct out of 160. That reads as +4.4 points. But accuracy hides two things:

- **Flips go both ways.** +7 net can be 12 questions fixed and 5 questions broken. The 5 broken ones are the regression nobody looked at.
- **160 questions is a small sample.** A +7 swing can happen by luck.

Shinrai looks only at the questions that flipped, because a question both runs got right (or both got wrong) says nothing about the change.

```
$ python -m shinrai compare examples/small/before.jsonl examples/small/after.jsonl
NOT PROVEN

questions compared : 160
accuracy           : 90.0% -> 94.4%  (+4.4 pts)
flips              : 12 wrong->right, 5 right->wrong
McNemar p-value    : 0.1435
95% CI of change   : [-0.6 pts, +9.4 pts]  (paired bootstrap)

by tag (n, gained, lost):
  ...
  card_lost        20    3    5   <- got worse
  ...

right->wrong ids (check these first): q020, q021, q025, q034, q036
```

Same headline gain direction, more decisive flips (`examples/big`, 15 fixed and 1 broken): **REAL GAIN**, CI [+4.4, +13.8] pts.

The example flip counts are invented to show the method; they are not from any real model.

## What it checks

| Check | Why |
|---|---|
| **Flip counts** (wrong→right, right→wrong) | Net accuracy hides regressions. |
| **Exact McNemar test** | If the change did nothing, each flip is a coin toss: is the split too lopsided for luck? |
| **Paired bootstrap 95% CI** | Resample questions (keeping each before/after pair together): the range the true change plausibly lies in. Seeded, so it is repeatable. |
| **Per-tag breakdown** | A gain overall can hide a slice that got worse (`card_lost` above). |
| **Missing ids** | Questions in only one run are reported, never silently dropped: a run that skipped hard questions would look better. |

Verdict: `REAL GAIN` when p < α **and** the whole CI is above 0; `REAL REGRESSION` when it is all below 0; otherwise `NOT PROVEN`. Exit codes 0 / 2 / 1, so it can gate CI.

## Use it

Each run is JSONL, one line per question, matched by `id`:

```json
{"id": "q001", "correct": true, "tag": "refund"}
{"id": "q002", "pred": "card_lost", "gold": "card_lost"}
```

```bash
python -m shinrai compare before.jsonl after.jsonl            # text report
python -m shinrai compare before.jsonl after.jsonl --json     # for dashboards
python -m shinrai compare before.jsonl after.jsonl --alpha 0.01 --seed 3
python -m unittest discover -s tests                          # 10 tests
```

Standard library only, Python 3.10+.

## Limits

- It tells you whether a difference is **real**, not whether it is **big enough to matter**. Look at the CI's size for that.
- One run per side. With sampling (temperature > 0), run each side several times; seed variance is the next feature.
- Checking many tags at once raises the chance one looks worse by luck; treat tag flags as "look here", not proof.

## Related

- [Kensa](https://github.com/nancy6547/kensa): metamorphic tests for RAG (what should change when the input changes).
- [HalluGuard](https://github.com/nancy6547/halluguard): sentence-level hallucination check, benchmarked with thresholds frozen before test.

MIT License.
