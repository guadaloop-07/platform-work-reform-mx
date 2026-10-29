"""Stage the reviewed ENOE 2025 Q3 release without interpreting source bytes."""

import argparse
import csv
import hashlib
import io
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import psycopg

from platform_work_reform.config import Settings
from platform_work_reform.enoe_contract import (
    DWELLING,
    HOUSEHOLD,
    PERSON,
    RELATIONSHIPS,
    key_fields,
    validate_header,
)


@dataclass(frozen=True)
class TableContract:
    name: str
    key: tuple[str, ...]
    rows: int
    member_sha256: str
    dictionary_sha256: str


ARCHIVE_SHA256 = "7138b2bfabc740a9805b83b3fd0dae28287fc2aab3781a596a741b8fc7861566"
CONTRACTS = (
    TableContract(
        "VIV",
        DWELLING,
        150405,
        "c3e11e1b0d5e5b30f5763022c803e2e26667a97acd74b1a64aa3e8d1f837b327",
        "f96bb59f2cab419f32dfe458101d40932ba2a843c6822081522e50962e5a1d55",
    ),
    TableContract(
        "HOG",
        HOUSEHOLD,
        151354,
        "dfacd7dcc594f5a09a869fa571154529a3efb432b94b4b865a4675094dbf7b84",
        "d3cb0aba6335af39a54c3528eded42878373aa8c13470fb8e07fe32f176bc8a6",
    ),
    TableContract(
        "SDEM",
        PERSON,
        422306,
        "04bd5d5f9668848ac6c435f29abe3b20e6693f02f2ee880a1e9dc0aab1c94c9d",
        "43dd74055f8d4c934c5101b68f70065517f4a4b538d8230592e273b4c0ec6cbe",
    ),
    TableContract(
        "COE1",
        PERSON,
        346524,
        "aafec7839128b296bded5b4160e73f251ccc807b8f863731d8258f9206fe1ae2",
        "864e2fec3efd90fd72c1ac6aa8f6e81f9d3386bcb67c69237794c7f3aef793c8",
    ),
    TableContract(
        "COE2",
        PERSON,
        346524,
        "66bae80c474b5c4ae0d855afb96c69593c053ba694b6caa6cf770c492ce1585b",
        "7bae811cbb54235ed8c8e87e2a810fa6db17f0bfde0ef58d18fc0f27b52d56f6",
    ),
)


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def members(table: str) -> tuple[str, str]:
    name = table.lower()
    base = f"conjunto_de_datos_{name}_enoe_2025_3t"
    return (
        f"{base}/conjunto_de_datos/{base}.csv",
        f"{base}/diccionario_de_datos/diccionario_datos_{name}_enoe_2025_3t.csv",
    )


def member_digest(archive: zipfile.ZipFile, member: str) -> str:
    with archive.open(member) as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(settings: Settings, source: Path) -> dict[str, int]:
    """Load only the exact reviewed release, atomically and without source mutation."""
    if source.is_symlink() or not source.is_file() or digest(source) != ARCHIVE_SHA256:
        raise ValueError("Source is not the reviewed ENOE 2025 Q3 archive")
    with (
        zipfile.ZipFile(source) as archive,
        psycopg.connect(**settings.connection_parameters()) as conn,
    ):
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate archive member")
        source_id = conn.execute(
            """INSERT INTO meta.source_file
               (source_name, original_name, sha256, byte_size, source_uri, encoding)
               VALUES ('enoe', %s, %s, %s, %s, 'binary-field-values')
               ON CONFLICT (source_name, sha256) DO UPDATE SET sha256=EXCLUDED.sha256
               RETURNING id""",
            (
                source.name,
                ARCHIVE_SHA256,
                source.stat().st_size,
                "https://www.inegi.org.mx/contenidos/programas/enoe/15ymas/datosabiertos/2025/"
                "conjunto_de_datos_enoe_2025_3t_csv.zip",
            ),
        ).fetchone()[0]
        existing = conn.execute(
            "SELECT run_id FROM staging.enoe_load WHERE source_file_id=%s AND reference_period=%s",
            (source_id, date(2025, 7, 1)),
        ).fetchone()
        if existing:
            return dict(
                conn.execute(
                    "SELECT table_name, row_count FROM staging.enoe_table WHERE run_id=%s",
                    (existing[0],),
                ).fetchall()
            )
        run_id = conn.execute(
            "INSERT INTO meta.ingestion_run(source_file_id,status,started_at) "
            "VALUES (%s,'running',now()) RETURNING id",
            (source_id,),
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO staging.enoe_load(run_id,source_file_id,reference_period,layout_version) "
            "VALUES (%s,%s,%s,%s)",
            (run_id, source_id, date(2025, 7, 1), "enoe-2025q3-v1"),
        )
        counts = {}
        for contract in CONTRACTS:
            data, dictionary = members(contract.name)
            if (
                member_digest(archive, data) != contract.member_sha256
                or member_digest(archive, dictionary) != contract.dictionary_sha256
            ):
                raise ValueError(f"Unexpected {contract.name} source or dictionary")
            with archive.open(dictionary) as raw:
                reader = csv.DictReader(
                    io.TextIOWrapper(raw, encoding="utf-8", errors="strict", newline="")
                )
                expected_header = [row["NEMÓNICO"] for row in reader]
            with (
                archive.open(data) as raw,
                io.TextIOWrapper(raw, encoding="latin-1", errors="strict", newline="") as text,
            ):
                reader = csv.reader(text, strict=True)
                header = next(reader)
                validate_header(2025, 3, contract.name, header)
                if header != expected_header or contract.key != key_fields(2025, 3, contract.name):
                    raise ValueError(f"Unexpected {contract.name} header")
                indexes = [header.index(field) for field in contract.key]
                conn.execute(
                    "INSERT INTO staging.enoe_table(run_id,table_name,header,row_count,"
                    "member_sha256,dictionary_sha256) VALUES (%s,%s,%s,%s,%s,%s)",
                    (
                        run_id,
                        contract.name,
                        header,
                        contract.rows,
                        contract.member_sha256,
                        contract.dictionary_sha256,
                    ),
                )
                count = 0
                with conn.cursor().copy(
                    "COPY staging.enoe_row(run_id,table_name,row_number,source_key,raw_fields) "
                    "FROM STDIN"
                ) as copy:
                    for count, row in enumerate(reader, 1):
                        if len(row) != len(header):
                            raise ValueError(f"Malformed {contract.name} row {count}")
                        key = [row[i] for i in indexes]
                        if any(
                            not item.strip() or not item.isascii() or "\x00" in item for item in key
                        ):
                            raise ValueError(f"Invalid {contract.name} key at row {count}")
                        copy.write_row(
                            (
                                run_id,
                                contract.name,
                                count,
                                key,
                                [item.encode("latin-1") for item in row],
                            )
                        )
                if count != contract.rows:
                    raise ValueError(f"Unexpected {contract.name} row count")
                counts[contract.name] = count
        for parent, child in sorted(RELATIONSHIPS):
            width = len(key_fields(2025, 3, parent))
            orphan_count = conn.execute(
                """SELECT count(*) FROM staging.enoe_row c
                WHERE c.run_id=%s AND c.table_name=%s AND NOT EXISTS
                (SELECT 1 FROM staging.enoe_row p WHERE p.run_id=c.run_id AND p.table_name=%s
                 AND p.source_key=c.source_key[1:%s])""",
                (run_id, child, parent, width),
            ).fetchone()[0]
            if orphan_count:
                raise ValueError(f"Unmatched {child} keys against {parent}")
        if digest(source) != ARCHIVE_SHA256:
            raise ValueError("Source changed during loading")
        conn.execute(
            "UPDATE meta.ingestion_run SET status='succeeded',finished_at=now() WHERE id=%s",
            (run_id,),
        )
        return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    print(load(Settings.from_env(), args.archive))


if __name__ == "__main__":
    main()
