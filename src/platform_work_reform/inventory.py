"""Inventory monthly IMSS files without modifying source data."""

import argparse
import calendar
import hashlib
import json
import os
import re
import tempfile
from collections import defaultdict
from datetime import date
from pathlib import Path

PATTERN = re.compile(r"^asg-(\d{4}-\d{2}-\d{2})(?:[-_][^.]+)?\.csv$")


def inventory(root: Path, start: date, end: date) -> dict:
    root = root.resolve(strict=True)
    if not root.is_dir() or start > end:
        raise ValueError("Source must be a directory and start must not follow end")
    records = []
    for path in sorted(root.iterdir()):
        match = PATTERN.fullmatch(path.name)
        if not match:
            continue
        if not start.isoformat() <= match[1] <= end.isoformat():
            continue
        try:
            period = date.fromisoformat(match[1])
        except ValueError as exc:
            raise ValueError(f"Invalid date in filename: {path.name}") from exc
        if period.day != calendar.monthrange(period.year, period.month)[1]:
            raise ValueError(f"Expected month-end date: {path.name}")
        if not start <= period <= end:
            continue
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Expected a regular file: {path.name}")
        with path.open("rb") as stream:
            before = os.fstat(stream.fileno())
            checksum = hashlib.file_digest(stream, "sha256").hexdigest()
            after = os.fstat(stream.fileno())
        current = path.stat()

        def identity(stat):
            return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)

        if identity(before) != identity(after) or identity(after) != identity(current):
            raise ValueError(f"File changed while hashing: {path.name}")
        records.append(
            {
                "name": path.name,
                "period": period.isoformat(),
                "size_bytes": before.st_size,
                "sha256": checksum,
            }
        )
    by_hash, by_period = defaultdict(list), defaultdict(set)
    for record in records:
        by_hash[record["sha256"]].append(record["name"])
        by_period[record["period"]].add(record["sha256"])
    return {
        "source_directory": str(root),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "files": records,
        "duplicate_content": [names for names in by_hash.values() if len(names) > 1],
        "periods_with_revisions": sorted(p for p, hashes in by_period.items() if len(hashes) > 1),
    }


def write_manifest(root: Path, start: date, end: date, output: Path) -> None:
    root = root.resolve(strict=True)
    output = output.resolve()
    if output == root or root in output.parents:
        raise ValueError("Manifest must be written outside the source directory")
    if output.exists():
        raise FileExistsError("Manifest already exists")
    result = inventory(root, start, end)
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".inventory-", dir=output.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--start", required=True, type=date.fromisoformat)
    parser.add_argument("--end", required=True, type=date.fromisoformat)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        write_manifest(args.source, args.start, args.end, args.output)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Inventory failed: {exc}\n")
    print(f"Inventory saved to {args.output}")


if __name__ == "__main__":
    main()
