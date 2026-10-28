"""Explicit layouts for monthly IMSS insured-person aggregate files."""

import csv
from collections.abc import Iterator
from pathlib import Path

DIMENSIONS = (
    "cve_delegacion",
    "cve_subdelegacion",
    "cve_entidad",
    "cve_municipio",
    "sector_economico_1",
    "sector_economico_2",
    "sector_economico_4",
    "tamaño_patron",
    "sexo",
    "rango_edad",
    "rango_salarial",
    "rango_uma",
)
METRICS = (
    "asegurados",
    "no_trabajadores",
    "ta",
    "teu",
    "tec",
    "tpu",
    "tpc",
    "ta_sal",
    "teu_sal",
    "tec_sal",
    "tpu_sal",
    "tpc_sal",
    "masa_sal_ta",
    "masa_sal_teu",
    "masa_sal_tec",
    "masa_sal_tpu",
    "masa_sal_tpc",
)
LEGACY = DIMENSIONS + METRICS
PLATFORM = DIMENSIONS[:4] + ("ptpd",) + DIMENSIONS[4:] + METRICS


def layout(header: list[str]) -> str:
    if tuple(header) == LEGACY:
        return "legacy-v1"
    if tuple(header) == PLATFORM:
        return "platform-v1"
    raise ValueError("Unknown IMSS CSV layout")


def rows(path: Path, encoding: str) -> Iterator[tuple[str, list[str]]]:
    """Yield validated-width rows; values remain verbatim, including NA and blanks."""
    with path.open("r", encoding=encoding, errors="strict", newline="") as stream:
        reader = csv.reader(stream, delimiter="|", strict=True)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise ValueError("Empty IMSS CSV") from exc
        version = layout(header)
        for row in reader:
            if len(row) != len(header):
                raise ValueError(f"Invalid column count near line {reader.line_num}")
            yield version, row
