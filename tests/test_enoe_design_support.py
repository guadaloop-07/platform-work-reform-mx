import pytest

from platform_work_reform.enoe_design_support import DesignSupport


def record(**changes):
    return {
        "cve_ent": "01",
        "est_d_tri": "001",
        "upm": "001",
        "eda": "30",
        "r_def": "0",
        "c_res": "1",
        "fac_tri": "10",
        "clase1": "1",
        "clase2": "1",
        **changes,
    }


def test_domain_singleton_retains_zero_contributing_parent_clusters():
    audit = DesignSupport()
    audit.add(record())
    audit.add(record(upm="002", eda="10", clase1="", clase2=""))
    audit.add(record(est_d_tri="002", upm="003", eda="10", clase1="", clase2=""))
    report = audit.report()
    parent = report["groups"]["completed_residents"]
    domain = report["groups"]["population_15_plus"]
    assert parent["observed_nested_upms"] == 3
    assert parent["singleton_strata"] == 1
    assert domain["singleton_strata"] == 1
    assert domain["domain_support_in_completed_resident_strata"] == {
        "zero_domain_upms": 1,
        "one_domain_upm": 1,
        "two_or_more_domain_upms": 0,
        "parent_upms_without_domain_records": 2,
    }
    assert report["weighted_totals"] == {"population": 10, "pea": 10, "occupied": 10}
    assert report["variance_ready"] is False


def test_entity_nesting_and_multiple_people_do_not_multiply_upms():
    audit = DesignSupport()
    audit.add(record())
    audit.add(record())
    audit.add(record(cve_ent="02"))
    report = audit.report()["groups"]["completed_residents"]
    assert report["records"] == 3
    assert report["observed_strata"] == 2
    assert report["observed_nested_upms"] == 2
    assert report["upms_per_stratum_histogram"] == {1: 2}


def test_nonresponse_support_is_reported_without_treating_it_as_response():
    audit = DesignSupport()
    audit.add(record())
    audit.add(record(upm="002", r_def="15", eda="", fac_tri=""))
    audit.add(record(r_def="15", eda="", cve_ent="", fac_tri=""))
    report = audit.report()["groups"]
    assert report["all_observed"]["observed_nested_upms"] == 2
    assert report["all_observed"]["records_with_invalid_design_keys"] == 1
    assert report["completed_residents"]["observed_nested_upms"] == 1


@pytest.mark.parametrize("key", ["cve_ent", "est_d_tri", "upm"])
@pytest.mark.parametrize("value", ["", "0", "NA", "１", "-1"])
def test_invalid_resident_design_key_fails_even_outside_age_domain(key, value):
    with pytest.raises(ValueError, match="design key"):
        DesignSupport().add(record(eda="10", **{key: value}))


def test_activity_restriction_does_not_remove_parent_support():
    audit = DesignSupport()
    audit.add(record())
    audit.add(record(upm="002", clase1="2", clase2="3"))
    report = audit.report()["groups"]
    assert report["population_15_plus"]["singleton_strata"] == 0
    assert report["pea"]["singleton_strata"] == 1
    assert (
        report["pea"]["domain_support_in_completed_resident_strata"][
            "parent_upms_without_domain_records"
        ]
        == 1
    )


def test_ordered_field_fingerprint_detects_changes_hidden_by_aggregates():
    original, reordered = DesignSupport(), DesignSupport()
    rows = [record(), record(upm="002")]
    for row in rows:
        original.add(row)
    for row in reversed(rows):
        reordered.add(row)
    assert original.report()["groups"] == reordered.report()["groups"]
    assert original.report()["ordered_fields_sha256"] != reordered.report()["ordered_fields_sha256"]
