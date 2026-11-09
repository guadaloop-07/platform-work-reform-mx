import csv
import hashlib
import io
import zipfile

import pytest

from platform_work_reform import enoe_variable_audit as module
from platform_work_reform.enoe_contract import HEADER_SIGNATURES, key_fields
from platform_work_reform.enoe_staging import members


def test_catalogue_anomaly_is_explicit_and_leading_zeros_survive():
    raw = b"CVE,DESCRIP\n01,Example\n1,Other\n"
    assert set(module.parse_catalogue(raw)) == {"01", "1"}
    malformed = b"CVE,DESCRIP,\n0,No aplica,\n1,Profesionales, tecnicos\n"
    with pytest.raises(ValueError, match="width"):
        module.parse_catalogue(malformed)
    assert module.parse_catalogue(malformed, anomalous=True)["1"] == "Profesionales, tecnicos"
    for raw in [b"CVE\n", b"CVE,DESCRIP\n1,A\n1,B\n", b"CVE,DESCRIP\n2,A,B\n"]:
        with pytest.raises(ValueError):
            module.parse_catalogue(raw)


def test_states_do_not_conflate_missingness_with_no_access():
    codes = {"0": "No aplica", "1": "IMSS", "6": "No care", "9": "Unknown"}
    assert module.state("p6d", None, codes) == "missing_questionnaire"
    assert module.state("p6d", "", codes) == "blank_routing_unresolved"
    assert module.state("p6d", "9", codes) == "unspecified"
    assert module.state("p6d", "6", codes) == "substantive_code"
    assert module.state("seg_soc", "0", codes) == "coded_not_applicable"
    assert module.state("p6d", "01", codes) == "invalid_code"
    assert (
        module.state(
            "p4a", "4899", {"4899": "Descripciones insuficientemente especificadas de subsector"}
        )
        == "insufficient_detail"
    )


def test_fingerprint_detects_selected_values_key_order_and_whitespace():
    first = module.fingerprint([(1, ("01",), ("1 ",))])
    assert first != module.fingerprint([(1, ("01",), ("1",))])
    assert first != module.fingerprint([(1, ("1",), ("1 ",))])
    with pytest.raises(ValueError, match="row numbers"):
        module.fingerprint([(2, ("01",), ("1 ",))])


def synthetic_archive(tmp_path, monkeypatch, *, completed="0"):
    path = tmp_path / "variables.zip"
    with zipfile.ZipFile(path, "w") as archive:
        for table in module.FIELDS:
            fields = (
                (*module.BASE, *module.FIELDS[table]) if table == "SDEM" else module.FIELDS[table]
            )
            header = [*key_fields(2025, 3, table), *fields]
            monkeypatch.setitem(
                HEADER_SIGNATURES,
                table,
                (
                    len(header),
                    hashlib.sha256("\n".join(header).encode()).hexdigest(),
                ),
            )
            rows = [header]
            for number in range(1, 5):
                if table != "SDEM" and number in (2, 4):
                    continue
                values = dict.fromkeys(header, "1")
                values["n_ren"] = str(number)
                values.update(
                    eda="30",
                    r_def=completed,
                    c_res="1",
                    fac_tri=str(number * 10),
                    clase1="1",
                    clase2="1",
                )
                if number == 2:
                    values.update(eda="98", seg_soc="0", pos_ocu="99")
                if number == 3:
                    values.update(clase1="2", clase2="3")
                if number == 4:
                    values.update(eda="99")
                values.update(p3="9999", p4a="", p6d="6", p7="9")
                rows.append([values[f] for f in header])
            stream = io.StringIO(newline="")
            csv.writer(stream).writerows(rows)
            archive.writestr(members(table)[0], stream.getvalue())
    return path


@pytest.mark.parametrize("completed", ["0", "00"])
def test_profile_occupied_domain_weights_missing_questionnaires_and_age98(
    tmp_path,
    monkeypatch,
    completed,
):
    path = synthetic_archive(tmp_path, monkeypatch, completed=completed)
    codes = {
        f: {"0": "NA", "1": "Yes", "6": "No", "9": "Unknown", "9999": "Unknown"}
        for fields in module.FIELDS.values()
        for f in fields
    }
    with zipfile.ZipFile(path) as archive:
        result = module.profile(archive, 2025, 3, codes, completed)
    assert result["flow_counts"]["occupied"] == 2
    assert result["flow_counts"]["eligible_not_occupied"] == 1
    assert result["flow_counts"]["outside_national_universe"] == 1
    assert result["flow_weighted_totals"]["occupied"] == 30
    assert result["fields"]["p6d"]["states"] == {
        "substantive_code": 1,
        "missing_questionnaire": 1,
    }
    assert result["fields"]["p6d"]["weighted_states"]["missing_questionnaire"] == 20
    assert result["fields"]["pos_ocu"]["states"]["invalid_code"] == 1
    assert "99" not in result["fields"]["pos_ocu"]["observed_code_counts"]
    assert result["fields"]["p4a"]["states"]["blank_routing_unresolved"] == 1
    assert result["fields"]["p3"]["states"]["unspecified"] == 1


def test_duplicate_periods_fail_before_reading_data():
    with pytest.raises(ValueError, match="unique quarter"):
        module.compare(None, [{"year": 2025, "quarter": 3}] * 2)


def test_medical_reference_uses_p6d_two_to_four_in_same_group():
    result = {
        "cross_tabs": {
            "p4_p6d": [{"codes": ["4", "blank_routing_unresolved"], "rows": 1}],
            "p6d_imssissste": [
                {"codes": ["2", "2"], "rows": 3, "weighted_total": 30},
                {
                    "codes": ["blank_routing_unresolved", "unspecified"],
                    "rows": 1,
                    "weighted_total": 10,
                },
            ],
            "p6d_seg_soc": [{"codes": ["2", "1"], "rows": 3, "weighted_total": 30}],
        }
    }
    checks = module.reference_agreement(result)
    assert checks["p6d_imssissste"]["mismatched_rows"] == 0
    assert checks["p6d_imssissste"]["compared_rows"] == 4
    result["cross_tabs"]["p4_p6d"][0]["codes"][0] = "1"
    result["cross_tabs"]["p6d_seg_soc"][0]["codes"][1] = "2"
    checks = module.reference_agreement(result)
    assert not checks["abroad_blank_equivalence_observed"]
    assert checks["p6d_imssissste"]["unresolved_rows"] == 1
    assert checks["p6d_seg_soc"]["mismatched_rows"] == 3
    assert checks["p6d_seg_soc"]["mismatched_weighted_total"] == 30
