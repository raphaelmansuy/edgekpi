"""Arithmetic behind ../BUSINESS-CASE.md, ../03-problem-catalogue.md and ../16-correctness-contract.md.

Exact rational arithmetic only: no SQL engine and no product code is exercised.
"""
from fractions import Fraction as F


def test_mean_of_rates_error_is_group_count_times_covariance_of_weight_and_rate():
    """mean(r) - sum(w r) = -n Cov(w, r). The shortcut is exact only when group size and rate are
    uncorrelated; when the largest group has the lowest rate, the average flatters the total."""
    def gap_and_covariance(weights, rates):
        n, share = len(rates), [F(w, sum(weights)) for w in weights]
        mean = sum(rates) / n
        covariance = sum((s - F(1, n)) * (r - mean) for s, r in zip(share, rates)) / n
        return mean - sum(s * r for s, r in zip(share, rates)), covariance, n

    for weights, rates in [((90, 10), (F(9, 10), F(1, 2))), ((3, 1), (F(2, 3), F(1))), ((450, 300, 300), (F(385, 450), F(245, 300), F(235, 300)))]:
        gap, covariance, n = gap_and_covariance(weights, rates)
        assert gap == -n * covariance and gap != 0
    assert gap_and_covariance((5, 5), (F(1, 5), F(4, 5)))[0] == 0    # equal weights
    assert gap_and_covariance((9, 1), (F(1, 2), F(1, 2)))[0] == 0    # equal rates

    gap, covariance, _n = gap_and_covariance((600, 300, 100), (F(2, 10), F(5, 10), F(9, 10)))
    assert covariance < 0 < gap  # largest group, lowest rate: the average overstates


def test_displayed_rates_alone_cannot_determine_the_total():
    """Same two displayed rates, different denominators, different correct totals: no formula over the
    displayed percentages can be right in both cases. The total always stays between the child rates."""
    rates = (F(1, 2), F(9, 10))
    totals = [F(sum(d * r for d, r in zip(denominators, rates)), sum(denominators)) for denominators in ((2, 10), (10, 10), (30, 10))]
    assert totals == [F(5, 6), F(7, 10), F(3, 5)]
    assert all(min(rates) <= t <= max(rates) for t in totals)


def test_distinct_scalars_only_bound_the_total():
    """max(parts) <= |union| <= sum(parts), and both ends are reachable from the same displayed counts."""
    a = {"c1", "c2", "c3"}
    for b, union in (({"c1", "c2", "c3"}, 3), ({"c3", "c4", "c5"}, 5), ({"c4", "c5", "c6"}, 6)):
        assert len(b) == 3 and len(a | b) == union
        assert max(len(a), len(b)) <= len(a | b) <= len(a) + len(b)


def test_a_correct_total_can_reverse_a_comparison_and_the_gap_splits_into_mix_and_rate():
    """Simpson's reversal: VIP opens more than New within each campaign and less overall, because VIP
    messages sit mostly in the low-open campaign. Totals are correct; the comparison needs the breakdown.
    Gap = mix effect + rate effect, an exact identity (C-CONTEXT)."""
    opened = {"New": {"promo": 720, "newsletter": 20}, "VIP": {"promo": 90, "newsletter": 270}}
    delivered = {"New": {"promo": 900, "newsletter": 100}, "VIP": {"promo": 100, "newsletter": 900}}
    rate = {s: {c: F(opened[s][c], delivered[s][c]) for c in opened[s]} for s in opened}
    share = {s: {c: F(delivered[s][c], sum(delivered[s].values())) for c in delivered[s]} for s in delivered}
    overall = {s: F(sum(opened[s].values()), sum(delivered[s].values())) for s in opened}

    assert all(rate["VIP"][c] > rate["New"][c] for c in rate["VIP"])
    assert overall == {"New": F(74, 100), "VIP": F(36, 100)}
    mix = sum((share["VIP"][c] - share["New"][c]) * (rate["VIP"][c] + rate["New"][c]) / 2 for c in rate["VIP"])
    within = sum((share["VIP"][c] + share["New"][c]) / 2 * (rate["VIP"][c] - rate["New"][c]) for c in rate["VIP"])
    assert (mix, within) == (F(-48, 100), F(10, 100))
    assert mix + within == overall["VIP"] - overall["New"] == F(-38, 100)
