from decimal import Decimal

import pytest

from platform_work_reform.imss_platform_series import summarize


def test_partition_and_real_zero():
    result = summarize(
        "platform-v1",
        [("1", 2, Decimal(7), 0, 0), ("0", 1, Decimal(3), 0, 0), (None, 1, Decimal(0), 0, 0)],
        (4, Decimal(10), 0, 0),
    )
    assert result["categories"]["platform"]["ta"] == "7"
    assert result["categories"]["missing"]["ta"] == "0"
    assert result["total_ta"] == "10"
    assert result["reconciled"]


def test_legacy_is_unavailable_and_partial_metrics_are_not_totals():
    result = summarize("legacy-v1", [(None, 2, Decimal(8), 1, 0)], (2, Decimal(8), 1, 0))
    assert result["classification_status"] == "unavailable"
    assert result["categories"]["platform"]["ta"] is None
    assert result["categories"]["missing"]["ta"] is None
    assert result["total_ta"] is None
    result = summarize("platform-v1", [("1", 1, None, 1, 0)], (1, None, 1, 0))
    assert result["categories"]["platform"]["ta"] is None
    assert result["categories"]["nonplatform"]["ta"] == "0"


@pytest.mark.parametrize("code", ["2", "01", " 1", "platform"])
def test_unknown_codes_fail(code):
    with pytest.raises(ValueError, match="Invalid ptpd"):
        summarize("platform-v1", [(code, 1, Decimal(1), 0, 0)], (1, Decimal(1), 0, 0))


def test_invalid_count_and_partition_mismatch_fail():
    with pytest.raises(ValueError, match="Invalid affiliated"):
        summarize("platform-v1", [("1", 1, Decimal(-1), 0, 1)], (1, Decimal(-1), 0, 1))
    with pytest.raises(ValueError, match="reconciliation"):
        summarize("platform-v1", [("1", 1, Decimal(1), 0, 0)], (1, Decimal(2), 0, 0))
    with pytest.raises(ValueError, match="Legacy"):
        summarize("legacy-v1", [("1", 1, Decimal(1), 0, 0)], (1, Decimal(1), 0, 0))
