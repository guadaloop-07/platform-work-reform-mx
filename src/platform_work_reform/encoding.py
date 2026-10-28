"""Strict, streaming encoding inspection and UTF-8 normalization."""

import argparse
import codecs
import hashlib
import os
import tempfile
from pathlib import Path

ENCODINGS = ("utf-8", "cp1252", "iso-8859-1")
CHUNK_SIZE = 1024 * 1024


def inspect(path: Path) -> dict:
    decoders = {name: codecs.getincrementaldecoder(name)(errors="strict") for name in ENCODINGS}
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        before = os.fstat(stream.fileno())
        prefix = stream.read(4)
        stream.seek(0)
        for block in iter(lambda: stream.read(CHUNK_SIZE), b""):
            digest.update(block)
            for name, decoder in list(decoders.items()):
                try:
                    decoder.decode(block, final=False)
                except UnicodeDecodeError:
                    del decoders[name]
        for name, decoder in list(decoders.items()):
            try:
                decoder.decode(b"", final=True)
            except UnicodeDecodeError:
                del decoders[name]
        after = os.fstat(stream.fileno())
    current = path.stat()

    def identity(s):
        return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)

    if identity(before) != identity(after) or identity(after) != identity(current):
        raise ValueError("Source changed during inspection")
    return {
        "sha256": digest.hexdigest(),
        "compatible": list(decoders),
        "utf8_bom": prefix.startswith(codecs.BOM_UTF8),
    }


def normalize(source: Path, output: Path, encoding: str) -> None:
    if encoding not in (*ENCODINGS, "utf-8-sig"):
        raise ValueError("Unsupported encoding")
    if source.is_symlink() or not source.is_file():
        raise ValueError("Source must be a regular non-symlink file")
    if source.resolve() == output.resolve() or output.exists():
        raise ValueError("Output must be a new file distinct from the source")
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".normalize-", dir=output.parent)
    temp = Path(name)
    try:
        with os.fdopen(fd, "wb") as target, source.open("rb") as stream:
            before = os.fstat(stream.fileno())
            decoder = codecs.getincrementaldecoder(encoding)(errors="strict")
            for block in iter(lambda: stream.read(CHUNK_SIZE), b""):
                target.write(decoder.decode(block, final=False).encode("utf-8"))
            target.write(decoder.decode(b"", final=True).encode("utf-8"))
            after = os.fstat(stream.fileno())
            now = source.stat()
            if any(
                (
                    before.st_size != after.st_size,
                    before.st_mtime_ns != after.st_mtime_ns,
                    before.st_ino != after.st_ino,
                    after.st_ino != now.st_ino,
                    after.st_size != now.st_size,
                    after.st_mtime_ns != now.st_mtime_ns,
                )
            ):
                raise ValueError("Source changed during normalization")
            target.flush()
            os.fsync(target.fileno())
        os.link(temp, output)
    finally:
        temp.unlink(missing_ok=True)


def main() -> None:
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    detect = sub.add_parser("inspect")
    detect.add_argument("source", type=Path)
    convert = sub.add_parser("normalize")
    convert.add_argument("source", type=Path)
    convert.add_argument("output", type=Path)
    convert.add_argument("--encoding", required=True, choices=(*ENCODINGS, "utf-8-sig"))
    args = parser.parse_args()
    try:
        if args.action == "inspect":
            print(json.dumps(inspect(args.source)))
        else:
            normalize(args.source, args.output, args.encoding)
    except (OSError, ValueError, UnicodeError) as exc:
        parser.exit(1, f"Encoding operation failed: {exc}\n")


if __name__ == "__main__":
    main()
