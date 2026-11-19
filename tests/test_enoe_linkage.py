"""Synthetic linkage fixtures exercise identity and retention risks, not real people."""

import pytest

from platform_work_reform.enoe_linkage import audit_pairs, pair_evidence


def person(**updates):
    row = dict(
        entity="01",
        con="40001",
        v_sel="01",
        n_hog="1",
        h_mud="0",
        n_ren="01",
        tipo="1",
        n_ent="2",
        sex="1",
        eda="30",
        nac_dia="01",
        nac_mes="01",
        nac_anio="1995",
        upm="0000001",
        cd_a="01",
        eligible=True,
        c_res="1",
        clase2="1",
        pos_ocu="3",
        p3="8342",
        p4a="4850",
        coe1_present=True,
        coe2_present=True,
    )
    return {**row, **updates}


def test_correct_continuity_does_not_require_same_occupation():
    a = person()
    b = person(n_ent="3", p3="2111", p4a="9999")
    result = audit_pairs([a], [b])["groups"]["passenger"]
    assert result["flow"]["supported_both_eligible"] == 1
    assert result["followup_availability"]["same_screen"] == 0
    assert result["supported_percent_of_continuing"] == 100


def test_both_periods_have_to_be_eligible_but_followup_is_not_filtered_before_link():
    result = audit_pairs([person()], [person(n_ent="3", eligible=False)])
    f = result["groups"]["passenger"]["flow"]
    assert f["supported_followup_outside_universe"] == 1
    assert f.get("supported_both_eligible", 0) == 0


@pytest.mark.parametrize(
    "field,value,conflict",
    [
        ("n_ent", "1", "interview_progression"),
        ("sex", "2", "sex"),
        ("eda", "29", "age"),
        ("eda", "32", "age"),
        ("nac_dia", "02", "nac_dia"),
        ("nac_mes", "02", "nac_mes"),
        ("nac_anio", "1994", "nac_anio"),
        ("upm", "0000002", "changed_upm"),
    ],
)
def test_conflicting_pair_is_quarantined(field, value, conflict):
    b = person(n_ent="3", **({field: value} if field != "n_ent" else {}))
    if field == "n_ent":
        b[field] = value
    e = pair_evidence(person(), b)
    assert conflict in e["conflicts"]
    assert not e["supported"]
    assert audit_pairs([person()], [b])["groups"]["passenger"]["flow"]["candidate_conflict"] == 1


def test_unknown_age_is_unresolved_even_with_matching_key():
    a, b = person(eda="98"), person(n_ent="3", eda="98")
    assert "age_unknown" in pair_evidence(a, b)["unresolved"]
    assert audit_pairs([a], [b])["groups"]["passenger"]["flow"]["candidate_unresolved"] == 1


def test_missing_birthdate_does_not_become_exact_birthdate_agreement():
    e = pair_evidence(
        person(nac_dia="99", nac_mes="99", nac_anio="9999"),
        person(n_ent="3", nac_dia="99", nac_mes="99", nac_anio="9999"),
    )
    assert e["supported"]  # Sex/age/context supported, not a birth-confirmed identity.
    assert e["birth_components_comparable"] == 0


def test_capped_age_is_not_treated_as_literal_age_97():
    assert pair_evidence(person(eda="97"), person(n_ent="3", eda="97"))["supported"]
    assert pair_evidence(person(eda="96"), person(n_ent="3", eda="97"))["supported"]
    assert not pair_evidence(person(eda="97"), person(n_ent="3", eda="96"))["supported"]


def test_household_replacement_is_not_same_person():
    result = audit_pairs([person()], [person(n_ent="3", h_mud="1")])
    f = result["groups"]["passenger"]["flow"]
    assert f["unmatched_household_replacement_possible"] == 1
    assert result["candidate_diagnostics"].get("candidate_pairs", 0) == 0


@pytest.mark.parametrize("side", ["baseline", "followup"])
def test_reduced_key_collisions_are_not_resolved_arbitrarily(side):
    a, b = person(), person(n_ent="3")
    first, second = ([a, {**a, "cd_a": "02"}], [b]) if side == "baseline" else ([a], [b, b])
    result = audit_pairs(first, second)
    f = result["groups"]["passenger"]["flow"]
    assert f[f"ambiguous_{side}_key"] == (2 if side == "baseline" else 1)
    assert f.get("supported_both_eligible", 0) == 0


def test_scheduled_rotation_is_separate_from_unmatched_continuers():
    rows = [person(n_ent="5"), person(n_ren="02")]
    f = audit_pairs(rows, [])["groups"]["passenger"]["flow"]
    assert f["baseline"] == 2
    assert f["scheduled_rotation_exit"] == 1
    assert f["continuing_baseline"] == 1
    assert f["unmatched_dwelling_not_in_sdem"] == 1


def test_retention_and_composition_include_unmatched_baseline_people():
    rows = [person(), person(n_ren="02", sex="2")]
    g = audit_pairs(rows, [person(n_ent="3")])["groups"]["passenger"]
    assert g["supported_percent_of_continuing"] == 50
    assert g["composition_sample_counts"]["supported|sex"] == {"1": 1}
    assert g["composition_sample_counts"]["other|sex"] == {"2": 1}


def test_month_is_not_a_cross_quarter_identifier_and_no_weight_is_summed():
    a = person(mes_cal="04", fac_tri="100")
    b = person(mes_cal="07", fac_tri="900", n_ent="3", eda="31")
    f = audit_pairs([a], [b])["groups"]["passenger"]["flow"]
    assert f["supported_both_eligible"] == 1
    assert all(isinstance(v, int) for v in f.values())


def test_empty_panel_reports_null_retention():
    assert audit_pairs([], [])["groups"]["passenger"]["supported_percent_of_continuing"] is None


def test_new_resident_cannot_be_accepted_as_existing_baseline_person():
    b = person(n_ent="3", c_res="3")
    assert "followup_new_resident" in pair_evidence(person(), b)["conflicts"]


def test_invalid_complete_birthdate_is_not_treated_as_missing():
    a, b = person(nac_mes="02", nac_dia="31"), person(n_ent="3", nac_mes="02", nac_dia="31")
    assert not pair_evidence(a, b)["supported"]


def test_collision_rows_remain_in_the_continuing_denominator():
    a = person()
    result = audit_pairs([a, {**a, "cd_a": "02"}], [person(n_ent="3")])
    g = result["groups"]["passenger"]
    assert g["flow"]["continuing_baseline"] == 2
    assert g["supported_percent_of_continuing"] == 0


def test_missing_context_is_unresolved_not_matching_blank_codes():
    e = pair_evidence(person(upm=""), person(n_ent="3", upm=""))
    assert "missing_upm" in e["unresolved"]
    assert not e["supported"]


def test_type_two_is_reported_as_excluded_not_as_attrition():
    g = audit_pairs([person(tipo="2")], [person(tipo="2", n_ent="3")])["groups"]["passenger"]
    assert g["flow"]["unsupported_type_or_missing_key"] == 1
    assert g["flow"]["continuing_baseline"] == 0
    assert g["supported_percent_of_continuing"] is None


def test_empty_groups_export_as_zero_sample_and_null_rate(tmp_path):
    from platform_work_reform.enoe_linkage import write_summary

    write_summary(tmp_path, audit_pairs([], []))
    assert "NA" in (tmp_path / "linkage.md").read_text()


def test_duplicate_manifest_fails_before_any_output(tmp_path, monkeypatch):
    import json
    import sys

    from platform_work_reform.enoe_linkage import main

    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps([{"year": 2025, "quarter": 2, "run_id": "a"}] * 2))
    output = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["linkage", str(manifest), "--output-dir", str(output)])
    with pytest.raises(ValueError, match="Duplicate"):
        main()
    assert not output.exists()
