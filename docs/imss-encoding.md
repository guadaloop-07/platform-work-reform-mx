# IMSS source encoding

Inspect entire files using `uv run --locked python -m platform_work_reform.encoding
inspect <file>`. The reported encodings are compatible candidates, not detected
truth. ASCII, ISO-8859-1 and CP1252 can be ambiguous, and valid UTF-8 can contain
already-corrupted text. Inspect source documentation and representative values.

After selecting and recording a justified encoding, `normalize <source> <new-output>
--encoding <encoding>` streams strict conversion to UTF-8. Existing outputs and
source overwrite are rejected. Errors leave no completed output. UTF-8 BOM can
be removed explicitly with `utf-8-sig`; `utf-8` preserves it.

This stage does not load PostgreSQL. Original files and temporary normalized files
remain outside Git. Compare source SHA-256 against the P06 manifest before use.
