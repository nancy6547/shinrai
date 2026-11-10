import contextlib
import io
import json
import tempfile
import unittest
from math import comb
from pathlib import Path

from shinrai import compare, load, mcnemar_exact, paired_bootstrap
from shinrai.cli import main


class TestStats(unittest.TestCase):
    def test_mcnemar_known_value(self):
        # 12 vs 5 flips: 2 * P(X <= 5), X ~ Bin(17, 0.5)
        expected = 2 * sum(comb(17, i) for i in range(6)) / 2**17
        self.assertAlmostEqual(mcnemar_exact(12, 5), expected)
        self.assertAlmostEqual(mcnemar_exact(5, 12), expected)  # symmetric

    def test_mcnemar_edges(self):
        self.assertEqual(mcnemar_exact(0, 0), 1.0)              # no flips = no evidence
        self.assertEqual(mcnemar_exact(3, 3), 1.0)              # even split
        self.assertLess(mcnemar_exact(15, 1), 0.001)

    def test_bootstrap_is_seeded_and_contains_delta(self):
        before = [True] * 80 + [False] * 20
        after = [True] * 90 + [False] * 10
        ci1 = paired_bootstrap(before, after, iters=2000, seed=3)
        ci2 = paired_bootstrap(before, after, iters=2000, seed=3)
        self.assertEqual(ci1, ci2)
        self.assertLessEqual(ci1[0], 0.10)
        self.assertGreaterEqual(ci1[1], 0.10)

    def test_bootstrap_identical_runs_is_zero(self):
        x = [True, False, True, True]
        self.assertEqual(paired_bootstrap(x, x, iters=500), (0.0, 0.0))


def write(d, name, rows):
    p = Path(d) / name
    p.write_text("\n".join(json.dumps(r) for r in rows))
    return p


class TestCompare(unittest.TestCase):
    def test_small_gain_is_not_proven(self):
        # 144 -> 151 of 160, 12 gained and 5 lost
        before = [{"id": i, "correct": i >= 16} for i in range(160)]
        after = [{"id": i, "correct": (i >= 16 and not 16 <= i < 21) or i < 12} for i in range(160)]
        with tempfile.TemporaryDirectory() as d:
            r = compare(load(write(d, "b", before)), load(write(d, "a", after)), iters=2000)
        self.assertEqual((len(r.gained), len(r.lost)), (12, 5))
        self.assertAlmostEqual(r.delta, 7 / 160)
        self.assertEqual(r.verdict, "NOT PROVEN")

    def test_big_gain_is_real(self):
        before = [{"id": i, "correct": i >= 16} for i in range(160)]
        after = [{"id": i, "correct": i != 159 and (i >= 16 or i < 15)} for i in range(160)]
        with tempfile.TemporaryDirectory() as d:
            r = compare(load(write(d, "b", before)), load(write(d, "a", after)), iters=2000)
        self.assertEqual(r.verdict, "REAL GAIN")
        self.assertGreater(r.ci[0], 0)

    def test_pred_gold_format_and_missing_ids(self):
        with tempfile.TemporaryDirectory() as d:
            b = write(d, "b", [{"id": "x", "pred": "a", "gold": "a"}, {"id": "y", "pred": "b", "gold": "a"}])
            a = write(d, "a", [{"id": "x", "pred": "a", "gold": "a"}])
            r = compare(load(b), load(a), iters=200)
        self.assertEqual(r.n, 1)
        self.assertEqual(r.missing, ["y"])                     # reported, not silently dropped

    def test_duplicate_id_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = write(d, "b", [{"id": 1, "correct": True}, {"id": 1, "correct": False}])
            with self.assertRaises(ValueError):
                load(p)

    def test_slices_flag_the_tag_that_got_worse(self):
        before = [{"id": i, "correct": True, "tag": "a" if i < 5 else "b"} for i in range(10)]
        after = [{"id": i, "correct": i >= 2, "tag": "a" if i < 5 else "b"} for i in range(10)]
        with tempfile.TemporaryDirectory() as d:
            r = compare(load(write(d, "b", before)), load(write(d, "a", after)), iters=200)
        self.assertEqual(r.slices["a"], (5, 0, 2))
        self.assertEqual(r.slices["b"], (5, 0, 0))


class TestCli(unittest.TestCase):
    def test_exit_codes(self):
        before = [{"id": i, "correct": i >= 16} for i in range(160)]
        after = [{"id": i, "correct": i != 159 and (i >= 16 or i < 15)} for i in range(160)]
        with tempfile.TemporaryDirectory() as d:
            b, a = write(d, "b", before), write(d, "a", after)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                codes = [main(["compare", str(x), str(y), "--iters", "500"]) for x, y in [(b, a), (b, b), (a, b)]]
            self.assertEqual(codes, [0, 1, 2])
            self.assertIn("REAL GAIN", out.getvalue())


if __name__ == "__main__":
    unittest.main()
