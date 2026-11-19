"""Transition arithmetic and design-support diagnostics use synthetic sample records."""

import pytest

from platform_work_reform.enoe_transitions import (
    TransitionAudit,
    employment_state,
    write_transitions,
)


def row(**updates):
    return {
        "eligible": True,
        "clase2": "1",
        "emp_ppal": "1",
        "entity": "01",
        "est_d_tri": "0001",
        "upm": "0000001",
        "fac_tri": "999",
        **updates,
    }


def test_nonemployment_and_unknown_states_are_not_dropped_from_denominator():
    audit = TransitionAudit(["delivery"])
    for b in (
        row(emp_ppal="2"),
        row(clase2="2", emp_ppal="0"),
        row(clase2="4", emp_ppal="0"),
        row(emp_ppal=""),
    ):
        audit.add_pair(row(), b, ["delivery"], 3)
    s = audit.report()["groups"]["delivery"]["summary"]
    assert s["linked_baseline_informal_n"] == 4
    assert s["informal_to_formal_n"] == 1
    assert s["informal_to_formal_percent"] == 25
    assert s["informal_to_nonemployment_n"] == 2
    assert s["formal_to_informal_percent"] is None


def test_reverse_flow_and_full_birth_sensitivity_have_their_own_denominators():
    audit = TransitionAudit(["passenger"])
    audit.add_pair(row(), row(emp_ppal="2"), ["passenger"], 3)
    audit.add_pair(row(), row(), ["passenger"], 1)
    audit.add_pair(row(emp_ppal="2"), row(), ["passenger"], 3)
    g = audit.report()["groups"]["passenger"]
    assert g["summary"]["informal_to_formal_percent"] == 50
    assert g["summary"]["formal_to_informal_percent"] == 100
    assert g["full_birth_sensitivity"]["informal_to_formal_percent"] == 100
    assert g["full_birth_sensitivity"]["linked_n"] == 2


def test_event_support_is_counted_by_nested_baseline_design_without_weight_expansion():
    audit = TransitionAudit(["passenger"])
    for a in (row(), row(), row(upm="0000002"), row(est_d_tri="0002"), row(est_d_tri="")):
        audit.add_pair(a, row(emp_ppal="2"), ["passenger"], 3)
    r = audit.report()
    cell = next(
        c
        for c in r["groups"]["passenger"]["matrix"]
        if c["baseline_state"] == "informal" and c["followup_state"] == "formal"
    )
    assert cell["sample_n"] == 5
    assert cell["baseline_strata_with_events"] == 2
    assert cell["baseline_upms_with_events"] == 3
    assert cell["largest_upm_event_n"] == 2
    assert cell["missing_baseline_design_n"] == 1
    assert r["weighted"] is False
    assert r["precision_validated"] is False


def test_not_applicable_is_not_an_informal_code_and_invalid_codes_fail():
    assert employment_state(row(emp_ppal="0")) == "formality_not_applicable"
    assert employment_state(row(clase2="3", emp_ppal="0")) == "inactive"
    with pytest.raises(ValueError, match="emp_ppal"):
        employment_state(row(emp_ppal="9"))
    with pytest.raises(ValueError, match="eligible"):
        TransitionAudit(["g"]).add_pair(row(), row(eligible=False), ["g"], 3)


def test_retention_and_export_keep_all_cells_including_zero_and_unknown(tmp_path):
    audit = TransitionAudit(["g"])
    audit.add_baseline(row(), ["g"], "scheduled_rotation_exit")
    audit.add_baseline(row(), ["g"], "supported_both_eligible")
    audit.add_pair(row(), row(emp_ppal="2"), ["g"], 3)
    r = audit.report()
    assert sum(c["sample_n"] for c in r["groups"]["g"]["matrix"]) == 1
    assert sum(c["sample_n"] for c in r["groups"]["g"]["baseline_retention"]) == 2
    assert len(r["groups"]["g"]["matrix"]) == 36
    write_transitions(tmp_path, {"sample_transitions": r})
    assert len((tmp_path / "transitions.csv").read_text().splitlines()) == 37
    assert "unweighted" in (tmp_path / "transitions.md").read_text()
