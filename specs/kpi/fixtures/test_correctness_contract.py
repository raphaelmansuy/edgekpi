"""Small mathematical counterexamples for ../16-correctness-contract.md.

No warehouse, SQL engine or product implementation is exercised here.
Run with: python3 -m unittest discover -s specs/kpi/fixtures -p test_correctness_contract.py
"""
from fractions import Fraction
import unittest


def guarded_ratio(numerator, denominator):
    return None if denominator in (None, 0) or numerator is None else Fraction(numerator, denominator)


class CorrectnessContractTests(unittest.TestCase):
    def test_rate_total_weights_by_its_own_denominator(self):
        numerator, denominator = (1, 9), (2, 10)
        rates = [Fraction(n, d) for n, d in zip(numerator, denominator)]
        total = Fraction(sum(numerator), sum(denominator))
        weighted = sum(Fraction(d, sum(denominator)) * r for d, r in zip(denominator, rates))
        self.assertEqual(total, Fraction(5, 6))
        self.assertEqual(weighted, total)
        self.assertEqual(sum(rates) / len(rates), Fraction(7, 10))
        self.assertNotEqual(sum(rates) / len(rates), total)

    def test_sent_weights_cannot_replace_delivered_or_opened_weights(self):
        # Both campaigns sent ten messages, but delivered denominators differ.
        sent, delivered, opened = (10, 10), (2, 10), (1, 9)
        rate_by_campaign = [Fraction(o, d) for o, d in zip(opened, delivered)]
        sent_weighted = sum(s * r for s, r in zip(sent, rate_by_campaign)) / sum(sent)
        self.assertEqual(sent_weighted, Fraction(7, 10))
        self.assertEqual(Fraction(sum(opened), sum(delivered)), Fraction(5, 6))
        self.assertNotEqual(sent_weighted, Fraction(sum(opened), sum(delivered)))

    def test_equal_distinct_scalars_do_not_determine_union(self):
        hk = {"c1", "c2"}
        sg_overlap, sg_disjoint = {"c2", "c3"}, {"c3", "c4"}
        self.assertEqual(len(sg_overlap), len(sg_disjoint))
        self.assertEqual((len(hk | sg_overlap), len(hk | sg_disjoint)), (3, 4))
        self.assertEqual(hk | sg_overlap, sg_overlap | hk)
        self.assertEqual(hk | hk, hk)  # state union tolerates repeated identities

    def test_parent_and_children_are_not_disjoint_count_partitions(self):
        rows = {"m1", "m2", "m3"}
        children = ({"m1"}, {"m2", "m3"})
        self.assertEqual(set.union(*children), rows)
        self.assertFalse(children[0] & children[1])
        self.assertEqual(sum(map(len, children)), len(rows))
        self.assertNotEqual(len(rows) + sum(map(len, children)), len(rows))
        incomplete = ({"m1"}, {"m2"})
        self.assertNotEqual(set.union(*incomplete), rows)

    def test_ratio_cancellation_has_a_nonzero_domain(self):
        clicked, opened, delivered = 1, 2, 4
        nested = guarded_ratio(guarded_ratio(clicked, delivered), guarded_ratio(opened, delivered))
        self.assertEqual(nested, guarded_ratio(clicked, opened))
        # Tracking inconsistency: cancellation would turn NULL into a valid number.
        clicked, opened, delivered = 1, 1, 0
        nested = guarded_ratio(guarded_ratio(clicked, delivered), guarded_ratio(opened, delivered))
        self.assertIsNone(nested)
        self.assertEqual(guarded_ratio(clicked, opened), 1)

    def test_reading_prior_year_is_insufficient_without_display_alignment(self):
        source = {(2025, "HK"): 250, (2026, "HK"): 350}
        current = {(year, market): value for (year, market), value in source.items() if year == 2026}
        prior_unaligned = {(year, market): value for (year, market), value in source.items() if year == 2025}
        self.assertIsNone(prior_unaligned.get((2026, "HK")))
        prior_aligned = {(year + 1, market): value for (year, market), value in prior_unaligned.items()}
        self.assertEqual((current[(2026, "HK")], prior_aligned[(2026, "HK")]), (350, 250))

    def test_independent_population_totals_do_not_determine_conversion(self):
        reached = {"c1", "c2"}
        buyers_a, buyers_b = {"c1", "c2"}, {"c3", "c4"}
        self.assertEqual(len(buyers_a), len(buyers_b))
        self.assertEqual((len(reached & buyers_a), len(reached & buyers_b)), (2, 0))

    def test_latest_date_watermark_misses_backdated_correction(self):
        before = {"2026-11-01": 10, "2026-11-12": 20}
        after = {"2026-11-01": 15, "2026-11-12": 20}
        self.assertEqual(max(before), max(after))
        self.assertNotEqual(sum(before.values()), sum(after.values()))

    def test_zero_and_undefined_rate_are_different(self):
        self.assertEqual(guarded_ratio(0, 8), 0)
        self.assertIsNone(guarded_ratio(0, 0))
        self.assertIsNone(guarded_ratio(None, 8))


if __name__ == "__main__":
    unittest.main()
