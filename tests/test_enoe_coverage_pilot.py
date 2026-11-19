"""Behavioral checks use synthetic people, never empirical platform claims."""

import pytest

from platform_work_reform.enoe_coverage_pilot import GROUPS, Group, changes, groups


def person(weight="10"):
    return {
        "fac_tri": weight,
        "eda": "35",
        "sex": "2",
        "anios_esc": "12",
        "pos_ocu": "3",
        "t_tra": "2",
    }


def test_screens_are_independent_of_health_and_keep_freight_as_sensitivity():
    assert groups("8342", "4850") == ["passenger", "passenger_narrow", "transport_delivery_broad"]
    assert groups("8342", "9999") == ["passenger", "transport_delivery_broad"]
    assert groups("9723", "4611") == ["delivery", "transport_delivery_broad"]
    assert groups("8341", "4840") == ["transport_delivery_broad"]
    assert groups("9999", "4850") == []


def test_unknown_and_absent_questionnaires_are_not_known_negatives():
    g = Group()
    for weight, medical in (("10", "1"), ("20", "6"), ("30", "9"), ("40", ""), ("50", None)):
        g.add(person(weight), {"p4": "1"}, None if medical is None else {"p6d": medical})
    r = g.report()
    assert r["sample"]["all"] == 5
    assert r["weighted"]["all"] == 150
    assert r["imss_percent_all"] == pytest.approx(100 * 10 / 150)
    assert r["imss_percent_known"] == pytest.approx(100 * 10 / 30)
    assert r["weighted"]["unknown"] == 30
    assert r["weighted"]["blank_routing_unresolved"] == 40
    assert r["weighted"]["missing_coe2"] == 50
    assert sum(r["composition_weighted"]["sex"].values()) == 150


def test_empty_and_all_unknown_groups_do_not_become_zero_known_coverage():
    assert Group().report()["imss_percent_all"] is None
    g = Group()
    g.add(person(), {"p4": "4"}, {"p6d": ""})
    assert g.report()["imss_percent_known"] is None
    assert g.report()["weighted"]["foreign_work"] == 10


@pytest.mark.parametrize("weight", ["0", "-1", "1.5", "", "NaN"])
def test_invalid_weights_fail(weight):
    with pytest.raises(ValueError, match="weight"):
        Group().add(person(weight), {"p4": "1"}, {"p6d": "1"})


def test_invalid_medical_code_fails():
    with pytest.raises(ValueError, match="p6d"):
        Group().add(person(), {"p4": "1"}, {"p6d": "0"})


def test_same_quarter_change_is_percentage_points_and_preserves_missing():
    rows = []
    for period, rate in (("2025Q2", 10.0), ("2026Q2", 15.0)):
        rows.append(
            {
                "period": period,
                "groups": {
                    name: {"imss_percent_all": rate, "imss_percent_known": None} for name in GROUPS
                },
            }
        )
    result = changes(rows)
    assert result[0]["change_pp"] == 5
    assert result[1]["change_pp"] is None


def test_profile_preserves_universe_and_occupation_missingness(monkeypatch):
    from platform_work_reform import enoe_coverage_pilot as pilot

    class Archive:
        def read(self, path):
            if path.endswith("p3.csv"):
                return b"CVE,DESCRIP\n8342,Passenger\n9999,Unknown\n"
            if path.endswith("p4a.csv"):
                return b"CVE,DESCRIP\n4850,Passenger transport\n"
            return b"CVE,DESCRIP\n1,IMSS\n6,None\n9,Unknown\n"

    people = [
        {**person(), "r_def": "00", "c_res": "1", "clase1": "1", "clase2": "1"} for _ in range(3)
    ]
    # The third occupied person has no COE1 and must stay in the national base.
    data = {
        "SDEM": [((str(i),), row) for i, row in enumerate(people)],
        "COE1": [
            (("0",), {"p3": "8342", "p4a": "4850", "p4": "1"}),
            (("1",), {"p3": "9999", "p4a": "4850", "p4": "1"}),
        ],
        "COE2": [(("0",), {"p6d": "1"}), (("1",), {"p6d": "9"})],
    }
    monkeypatch.setattr(pilot, "records", lambda archive, table, *args: iter(data[table]))
    result = pilot.profile(Archive(), 2025, 4, "00")
    assert result["national"]["weighted_totals"]["occupied"] == 30
    assert result["occupied_flow"] == {
        "classified_occupation": 1,
        "unknown_occupation": 1,
        "missing_coe1": 1,
    }
    assert result["groups"]["passenger"]["sample"]["all"] == 1
    assert result["groups"]["passenger"]["imss_percent_all"] == 100
    # A release-specific completion code must not silently become another code.
    with pytest.raises(ValueError, match="Empty denominator"):
        pilot.profile(Archive(), 2025, 4, "0")


def test_manifest_duplicate_periods_fail_before_data_access(tmp_path, monkeypatch):
    import json
    import sys

    from platform_work_reform.enoe_coverage_pilot import main

    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps([{"year": 2025, "quarter": 2}] * 4))
    output = tmp_path / "output"
    monkeypatch.setattr(sys, "argv", ["pilot", str(manifest), "--output-dir", str(output)])
    with pytest.raises(ValueError, match="Exactly one"):
        main()
    assert not output.exists()
