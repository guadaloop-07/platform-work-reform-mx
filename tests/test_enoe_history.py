"""Historical comparisons use fixed-year synthetic rates and strict source contracts."""

import csv
import hashlib
import io
import zipfile

import pytest

from platform_work_reform.enoe_history import (
    GROUPS,
    PARITY_2025,
    PARITY_FIELDS,
    check_parity,
    compare,
    contracts,
)
from platform_work_reform.enoe_linkage import read_records
from platform_work_reform.enoe_staging import members


def summaries():
    return [
        {
            "year": y,
            "screen": n,
            "informal_to_formal_percent": p,
            "formal_to_informal_percent": 40 - p,
        }
        for y, p in ((2023, 10.0), (2024, 30.0), (2025, 15.0))
        for n in GROUPS
    ]


def test_contrasts_use_rates_and_equal_year_mean_without_significance_labels():
    r = compare(summaries())
    a = next(
        c for c in r if c["screen"] == "passenger" and c["metric"] == "informal_to_formal_percent"
    )
    assert a["difference_vs_2023_pp"] == 5
    assert a["difference_vs_2024_pp"] == -15
    assert a["difference_vs_prior_year_mean_pp"] == -5
    assert a["outside_two_prior_values"] is False
    assert "p_value" not in a
    assert len(r) == 10


def test_missing_estimate_is_not_zero_or_a_declared_anomaly():
    rows = summaries()
    rows[0]["informal_to_formal_percent"] = None
    c = compare(rows)[0]
    assert c["difference_vs_2023_pp"] is None
    assert c["difference_vs_prior_year_mean_pp"] is None
    assert c["outside_two_prior_values"] is None


def test_missing_or_duplicate_year_screen_fails():
    with pytest.raises(ValueError, match="Exactly one"):
        compare(summaries()[:-1])
    with pytest.raises(ValueError, match="Exactly one"):
        compare(summaries() + [summaries()[0]])


def test_parity_rejects_drift_in_any_2025_screen():
    data = {
        "sample_transitions": {
            "groups": {
                name: {"summary": dict(zip(PARITY_FIELDS, values, strict=True))}
                for name, values in PARITY_2025.items()
            }
        }
    }
    check_parity(data)
    data["sample_transitions"]["groups"]["delivery"]["summary"]["informal_to_formal_n"] += 1
    with pytest.raises(ValueError, match="parity"):
        check_parity(data)


def test_all_six_contracts_preserve_key_meanings_and_entity_transition():
    specs = contracts()
    assert len(specs) == 6
    assert specs["2023q2"]["entity_field"] == "ent"
    assert specs["2025q3"]["entity_field"] == "cve_ent"
    assert len({s["catalogues"]["emp_ppal"]["sha256"] for s in specs.values()}) == 1
    for spec in specs.values():
        assert (
            spec["reference_totals"]["pea"]
            == spec["reference_totals"]["occupied"] + spec["reference_totals"]["unemployed"]
        )


def test_historical_reader_keeps_exact_keys_and_rejects_bad_header_and_duplicates():
    header = ["tipo", "mes_cal", "cd_a", "ent", "con", "v_sel", "n_hog", "h_mud", "n_ren", "eda"]
    key = header[:-1]
    contract = {
        "header": header,
        "header_sha256": hashlib.sha256("\n".join(header).encode()).hexdigest(),
        "key": key,
    }
    row = ["1", "04", "01", "01", "40001", "01", "1", "0", "01", "30"]

    def archive(rows):
        stream = io.StringIO()
        writer = csv.writer(stream)
        writer.writerows([header, *rows])
        blob = io.BytesIO()
        with zipfile.ZipFile(blob, "w") as z:
            z.writestr(members("SDEM", 2023, 2)[0], stream.getvalue())
        blob.seek(0)
        return zipfile.ZipFile(blob)

    with archive([row]) as z:
        result = list(read_records(z, "SDEM", 2, ("eda",), year=2023, source_contract=contract))
        assert result[0][0] == tuple(row[:-1])
        assert result[0][1]["eda"] == "30"
    with archive([row, row]) as z, pytest.raises(ValueError, match="duplicate"):
        list(read_records(z, "SDEM", 2, ("eda",), year=2023, source_contract=contract))
    with archive([row]) as z, pytest.raises(ValueError, match="header"):
        list(
            read_records(
                z,
                "SDEM",
                2,
                ("eda",),
                year=2023,
                source_contract={**contract, "header_sha256": "bad"},
            )
        )
