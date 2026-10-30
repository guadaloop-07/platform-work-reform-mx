import pytest

from platform_work_reform.enoe_pilot_indicators import Audit


def record(**changes):
    return {
        "eda": "30",
        "r_def": "0",
        "c_res": "1",
        "fac_tri": "10",
        "clase1": "1",
        "clase2": "1",
    } | changes


def test_universe_weights_and_missing_questionnaires():
    audit = Audit()
    audit.add(record(), True, True)
    audit.add(record(eda="98", clase2="2", fac_tri="2"), True, True)
    audit.add(record(eda="99", clase1="0", clase2="0"), False, False)
    audit.add(record(eda="", r_def="15", c_res="", clase1="0", clase2="0"), False, False)
    output = audit.report()
    assert output["counts"] == {
        "sdem": 4,
        "coe1_matched": 2,
        "coe2_matched": 2,
        "eligible": 2,
        "outside_universe": 2,
    }
    assert output["weighted_totals"] == {
        "population": 12,
        "pea": 12,
        "occupied": 10,
        "unemployed": 2,
    }
    assert output["participation_percent_rounded"] == "100.0"
    assert output["unemployment_percent_rounded"] == "16.7"
    assert sum(output["questionnaire_missing_categories"].values()) == 2


@pytest.mark.parametrize(
    "changes",
    [
        {"eda": ""},
        {"eda": "100"},
        {"fac_tri": ""},
        {"fac_tri": "0"},
        {"clase1": "1", "clase2": "4"},
        {"clase1": "0", "clase2": "0"},
    ],
)
def test_invalid_in_universe_values_fail(changes):
    with pytest.raises(ValueError):
        Audit().add(record(**changes), True, True)
