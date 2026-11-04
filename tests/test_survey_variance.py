from fractions import Fraction
from itertools import combinations
from math import fsum, sqrt

import pytest

from platform_work_reform.survey_variance import Estimate, UPMTotal, estimate, normal_summary


def sample():
    return [
        UPMTotal("01", "A", "1", 10, 20),
        UPMTotal("01", "A", "2", 30, 40),
        UPMTotal("02", "A", "1", 20, 40),
        UPMTotal("02", "A", "2", 40, 80),
    ]


def test_hand_calculated_total_and_entity_nesting():
    # Two independent stratum contributions: (30-10)^2 + (40-20)^2.
    assert estimate(sample(), kind="total") == Estimate(100, 800)


def test_hand_calculated_ratio():
    # R=5/9; residual pair differences are -80/9 and 20/9.
    result = estimate(sample(), kind="ratio")
    assert result.value == pytest.approx(5 / 9)
    assert result.variance == pytest.approx(Fraction(17, 6561))


def test_zero_domain_upm_is_retained():
    rows = [UPMTotal("01", "A", "1", 10, 10), UPMTotal("01", "A", "2", 0, 0)]
    assert estimate(rows, kind="total") == Estimate(10, 100)
    assert estimate(rows, kind="ratio") == Estimate(1, 0)
    with pytest.raises(ValueError, match="Singleton"):
        estimate(rows[:1], kind="total")


def test_independent_pairwise_exact_variance_identity():
    # k/(k-1) sum(z-mean)^2 = sum_{i<j}(z_i-z_j)^2/(k-1).
    xs, ys = [3, 8, 19, 21], [7, 13, 23, 27]
    rows = [UPMTotal("01", "A", str(i), x, y) for i, (x, y) in enumerate(zip(xs, ys, strict=True))]
    for kind in ("total", "ratio"):
        ratio = Fraction(sum(xs), sum(ys)) if kind == "ratio" else 0
        zs = [Fraction(x) - ratio * y for x, y in zip(xs, ys, strict=True)]
        pairwise = sum((a - b) ** 2 for a, b in combinations(zs, 2)) / (len(zs) - 1)
        expected = pairwise / sum(ys) ** 2 if kind == "ratio" else pairwise
        assert estimate(rows, kind=kind).variance == pytest.approx(float(expected))


@pytest.mark.parametrize(
    "confidence,critical", [(0.90, 1.6448536269514722), (0.95, 1.959963984540054)]
)
def test_normal_confidence_interval(confidence, critical):
    report = normal_summary(Estimate(100, 25), confidence=confidence)
    assert report["standard_error"] == 5
    assert report["cv_fraction"] == 0.05
    assert report["critical_value"] == pytest.approx(critical)
    assert report["interval"] == pytest.approx([100 - critical * 5, 100 + critical * 5])


def test_no_clipping_and_no_cv_for_zero_estimate():
    result = normal_summary(Estimate(0, 1), confidence=0.95)
    assert result["interval"][0] < 0
    assert result["cv_fraction"] is None


@pytest.mark.parametrize("value", [0, 1, -0.1, 90, float("nan"), float("inf"), 1 - 1e-16])
def test_invalid_confidence_fails(value):
    with pytest.raises(ValueError, match="Confidence"):
        normal_summary(Estimate(1, 1), confidence=value)


@pytest.mark.parametrize("value,variance", [(1, -1), (float("nan"), 1), (1, float("inf"))])
def test_invalid_summary_fails(value, variance):
    with pytest.raises(ValueError):
        normal_summary(Estimate(value, variance), confidence=0.95)


@pytest.mark.parametrize("kind", ["total", "ratio"])
def test_duplicate_and_singleton_support_fails(kind):
    with pytest.raises(ValueError, match="duplicate"):
        estimate([sample()[0], sample()[0]], kind=kind)
    with pytest.raises(ValueError, match="Singleton"):
        estimate(sample()[:3], kind=kind)
    with pytest.raises(ValueError, match="nonempty"):
        estimate([], kind=kind)


@pytest.mark.parametrize("x,y", [(float("nan"), 1), (1, float("inf")), (1, -1)])
def test_invalid_upm_totals_fail(x, y):
    with pytest.raises(ValueError, match="finite"):
        estimate([UPMTotal("01", "A", "1", x, y), sample()[1]], kind="ratio")


def test_undefined_ratio_and_numerical_overflow_fail():
    with pytest.raises(ValueError, match="denominator"):
        estimate([UPMTotal("01", "A", str(i), 1) for i in range(2)], kind="ratio")
    with pytest.raises(ValueError, match="overflow"):
        estimate(
            [UPMTotal("01", "A", str(i), x) for i, x in enumerate([1e308, -1e308])], kind="total"
        )


def test_scaling_to_percentage_scales_variance_and_standard_error():
    original = estimate(sample(), kind="ratio")
    scaled = estimate(
        [UPMTotal(r.entity, r.stratum, r.upm, r.x * 100, r.y) for r in sample()], kind="ratio"
    )
    assert scaled.value == pytest.approx(original.value * 100)
    assert scaled.variance == pytest.approx(original.variance * 10000)
    assert sqrt(scaled.variance) == pytest.approx(sqrt(original.variance) * 100)
    assert fsum([scaled.value, -original.value * 100]) == pytest.approx(0)


def test_zero_outcome_singleton_is_not_treated_as_certainty():
    with pytest.raises(ValueError, match="Singleton"):
        estimate([UPMTotal("01", "A", "1", 0)], kind="total")


def test_invalid_estimator_and_missing_key_fail():
    with pytest.raises(ValueError, match="supported estimator"):
        estimate(sample(), kind="unsupported")
    with pytest.raises(ValueError, match="key"):
        estimate([UPMTotal("", "A", "1", 10), sample()[1]], kind="total")


def test_explicit_three_decimal_critical_rounding():
    result = normal_summary(Estimate(100, 25), confidence=0.90, critical_decimals=3)
    assert result["unrounded_critical_value"] == pytest.approx(1.6448536269514722)
    assert result["critical_value"] == 1.645
    assert result["critical_rounding_decimals"] == 3
    assert result["interval"] == pytest.approx([91.775, 108.225])


@pytest.mark.parametrize("decimals", [-1, 13, 3.5, True])
def test_invalid_critical_rounding_fails(decimals):
    with pytest.raises(ValueError, match="decimals"):
        normal_summary(Estimate(1, 1), confidence=0.90, critical_decimals=decimals)
