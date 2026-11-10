"""Builds the example runs in this folder (deterministic).

Scenario: 160 banking-intent questions, 8 categories x 20.
  small/   : 144 -> 151 correct (+7). 12 gained, 5 lost.  Looks like a win.
  big/     : 144 -> 158 correct (+14). 15 gained, 1 lost.
The flip counts are made up for the example; they are not from any real run.
"""
import json
import random
from pathlib import Path

TAGS = ["balance", "card_lost", "transfer", "refund", "pin", "fees", "atm", "account"]
HERE = Path(__file__).parent


def build(name: str, gained: int, lost: int, lost_tag: str | None = None, seed: int = 7) -> None:
    rng = random.Random(seed)
    ids = [f"q{i:03d}" for i in range(160)]
    tag = {q: TAGS[i // 20] for i, q in enumerate(ids)}
    wrong_before = set(rng.sample(ids, 16))                 # 144 correct before
    right_before = [q for q in ids if q not in wrong_before]
    gain = set(rng.sample(sorted(wrong_before), gained))
    pool = [q for q in right_before if lost_tag is None or tag[q] == lost_tag]
    loss = set(rng.sample(pool, lost))
    d = HERE / name
    d.mkdir(exist_ok=True)
    with open(d / "before.jsonl", "w") as fb, open(d / "after.jsonl", "w") as fa:
        for q in ids:
            b = q not in wrong_before
            a = (b and q not in loss) or q in gain
            fb.write(json.dumps({"id": q, "correct": b, "tag": tag[q]}) + "\n")
            fa.write(json.dumps({"id": q, "correct": a, "tag": tag[q]}) + "\n")


if __name__ == "__main__":
    build("small", gained=12, lost=5, lost_tag="card_lost")
    build("big", gained=15, lost=1)
    print("wrote examples/small and examples/big")
