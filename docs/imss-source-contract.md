# IMSS monthly file contracts

The local files inspected have pipe-delimited CSV layouts with either the 29
legacy columns or 30 columns including `ptpd` after `cve_municipio`. Header order
is checked exactly, including `tamaño_patron`. Source values such as blank and
`NA` remain distinct strings until source-specific rules are documented.

The parser requires an explicit encoding and rejects malformed rows and unknown
headers. A missing `ptpd` is a missing source dimension, not zero. These contracts
describe observed files and do not assert that all official historical releases
have identical schemas. Publication and numerical conversions require separate
reconciliation; this stage does not load PostgreSQL.

Seven local files from 2023–2025 have a UTF-8 BOM in their header, while other
inspected headers use a single-byte encoding. Header compatibility alone does not
establish the encoding of an entire file. Use `utf-8-sig` explicitly for BOM files
and validate all bytes before selecting any single-byte encoding.
