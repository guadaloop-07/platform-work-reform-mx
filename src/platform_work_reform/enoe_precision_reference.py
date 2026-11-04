"""Check published interval arithmetic; this does not estimate sampling variance."""

import argparse
import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from platform_work_reform.enoe_staging import digest
from platform_work_reform.survey_variance import Estimate, normal_summary

REFERENCE_SHA256 = "d61aa638cde782555f77ce2ed55cd073a7d49b59a23bec4a46caa0a40095e099"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
HEADERS = {
    "D1": "Año",
    "F1": "Periodo",
    "G1": "Versión",
    "I1": "Clave_Entidad",
    "K1": "Dominio_estudio",
    "N1": "Variable",
    "O1": "Parametro",
    "P1": "Estimación",
    "Q1": "CV",
    "R1": "ErrorEst",
    "S1": "Niv_Conf",
    "T1": "IntConf_Inf",
    "U1": "IntConf_Sup",
}
VARIABLES = (
    "Población de 15 años y más",
    "Población económicamente activa (PEA)",
    "Población Desocupada",
    "Tasa de desocupación",
)


def read_cells(path: Path) -> dict:
    if digest(path) != REFERENCE_SHA256:
        raise ValueError("Unsupported precision-reference hash")
    with zipfile.ZipFile(path) as archive:
        strings = [
            "".join(t.text or "" for t in item.findall(".//m:t", NS))
            for item in ET.fromstring(archive.read("xl/sharedStrings.xml"))
        ]
        cells = {}
        for cell in ET.fromstring(archive.read("xl/worksheets/sheet1.xml")).findall(".//m:c", NS):
            value = cell.find("m:v", NS)
            if cell.attrib.get("t") == "s" and value is not None:
                text = strings[int(value.text)]
            elif value is not None:
                text = value.text
            else:
                text = "".join(t.text or "" for t in cell.findall(".//m:t", NS))
            cells[cell.attrib["r"]] = text
    return cells


def reconcile(cells: dict) -> dict:
    if any(cells.get(key) != value for key, value in HEADERS.items()):
        raise ValueError("Unsupported precision-reference header")
    references = []
    for row, variable in enumerate(VARIABLES, start=2):
        required = {
            "C": "ENOE",
            "D": "2025",
            "E": "Trimestral",
            "F": "III",
            "G": "Definitivo",
            "I": "00",
            "K": "Nacional",
            "N": variable,
            "S": "90",
            "O": "Tasa" if row == 5 else "Total",
        }
        if any(cells.get(f"{col}{row}") != value for col, value in required.items()):
            raise ValueError("Unsupported precision-reference population or period")
        value, cv, se, confidence, lower, upper = (
            float(cells[f"{col}{row}"]) for col in ("P", "Q", "R", "S", "T", "U")
        )
        calculated = normal_summary(
            Estimate(value, se * se), confidence=confidence / 100, critical_decimals=3
        )
        gaps = [calculated["interval"][0] - lower, calculated["interval"][1] - upper]
        # Counts have six-decimal serialized bounds; the published rate has six decimals.
        tolerance = 0.0000005 if row == 5 else 0.000001
        references.append(
            {
                "sheet": "INDICADORES",
                "row": row,
                "variable": variable,
                "estimate": value,
                "published_cv_percent": cv,
                "published_standard_error": se,
                "confidence_percent": confidence,
                "critical_value_used": calculated["critical_value"],
                "published_interval": [lower, upper],
                "interval_gaps": gaps,
                "absolute_tolerance": tolerance,
                "interval_arithmetic_match": all(abs(gap) <= tolerance for gap in gaps),
            }
        )
    return {
        "reference_sha256": REFERENCE_SHA256,
        "references": references,
        "reference_interval_arithmetic_match": all(
            r["interval_arithmetic_match"] for r in references
        ),
        "sampling_variance_validated": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    args = parser.parse_args()
    output = reconcile(read_cells(args.workbook))
    print(json.dumps(output, indent=2, sort_keys=True))
    if not output["reference_interval_arithmetic_match"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
