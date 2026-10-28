"""Run resumable, reconciled IMSS monthly loads from an inventory."""

import argparse
import calendar
import codecs
import json
import os
import subprocess
from datetime import UTC, date, datetime
from pathlib import Path

import psycopg

from platform_work_reform.config import Settings
from platform_work_reform.imss_contract import layout
from platform_work_reform.imss_publish import publish
from platform_work_reform.imss_staging import digest, load

MIN_FREE = 20 * 1024**3
NON_C1 = bytes([*range(128), *range(160, 256)])


def select_files(manifest: dict, start: date, end: date) -> list[dict]:
    if start > end:
        raise ValueError("Start must not follow end")
    selected = [x for x in manifest["files"] if start <= date.fromisoformat(x["period"]) <= end]
    selected.sort(key=lambda x: x["period"])
    periods = [x["period"] for x in selected]
    if len(periods) != len(set(periods)):
        raise ValueError("Multiple source versions require explicit selection")
    expected = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        expected.append(date(year, month, calendar.monthrange(year, month)[1]).isoformat())
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    if periods != expected:
        raise ValueError("Inventory does not cover every requested month")
    if any(Path(x["name"]).name != x["name"] for x in selected):
        raise ValueError("Inventory contains an invalid filename")
    return selected


def source_encoding(path: Path) -> str:
    """Resolve encodings only when byte-level evidence yields equivalent text."""
    with path.open("rb") as stream:
        header = stream.readline()
        if header.startswith(codecs.BOM_UTF8):
            layout(header.decode("utf-8-sig").rstrip("\r\n").split("|"))
            return "utf-8-sig"
        try:
            decoded = header.decode("utf-8")
        except UnicodeDecodeError:
            decoded = None
        if decoded is not None:
            layout(decoded.rstrip("\r\n").split("|"))
            return "utf-8"
        layout(header.decode("cp1252").rstrip("\r\n").split("|"))
        if header.translate(None, NON_C1):
            raise ValueError("Ambiguous CP1252 versus ISO-8859-1 header")
        while block := stream.read(1024 * 1024):
            if block.translate(None, NON_C1):
                raise ValueError("Ambiguous CP1252 versus ISO-8859-1 data")
    return "cp1252"


def database_free_bytes() -> int:
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "postgres", "df", "-Pk", "/var/lib/postgresql/data"],
        check=True,
        capture_output=True,
        text=True,
    )
    return int(result.stdout.strip().splitlines()[-1].split()[3]) * 1024


def selected_sha(settings: Settings, period: str) -> str | None:
    with psycopg.connect(**settings.connection_parameters()) as connection:
        value = connection.execute(
            """SELECT f.sha256 FROM imss.selected_month s
               JOIN staging.imss_load l ON l.run_id=s.run_id
               JOIN meta.source_file f ON f.id=l.source_file_id WHERE s.reference_period=%s""",
            (period,),
        ).fetchone()
        return value[0] if value else None


def append_status(path: Path, period: str, status: str, detail: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "period": period,
        "status": status,
        "detail": detail,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as stream:
        stream.write(json.dumps(record) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def run(
    settings: Settings, root: Path, manifest_path: Path, start: date, end: date, progress: Path
) -> None:
    root = root.resolve(strict=True)
    progress = progress.resolve()
    if progress == root or root in progress.parents:
        raise ValueError("Progress log must be outside the source directory")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = select_files(manifest, start, end)
    for item in files:
        period = item["period"]
        path = root / item["name"]
        print(f"{period}: checking", flush=True)
        try:
            selected = selected_sha(settings, period)
            if selected:
                if selected != item["sha256"] or digest(path) != item["sha256"]:
                    raise ValueError("Selected version or source hash differs from inventory")
                append_status(progress, period, "already_selected")
                print(f"{period}: already selected", flush=True)
                continue
            if database_free_bytes() < max(MIN_FREE, 10 * item["size_bytes"]):
                raise ValueError("Insufficient free space on database filesystem")
            encoding = source_encoding(path)
            count = load(settings, path, manifest_path, encoding)
            if publish(settings, path, manifest_path, encoding) != count:
                raise ValueError("Unexpected reconciled row count")
            append_status(progress, period, "selected", str(count))
            print(f"{period}: selected {count} rows", flush=True)
        except Exception as exc:
            append_status(progress, period, "failed", type(exc).__name__)
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--progress", type=Path, required=True)
    args = parser.parse_args()
    run(Settings.from_env(), args.root, args.manifest, args.start, args.end, args.progress)


if __name__ == "__main__":
    main()
