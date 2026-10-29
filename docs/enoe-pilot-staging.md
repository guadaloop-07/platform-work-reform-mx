# ENOE 2025 Q3 pilot staging

This pilot accepts only the exact national 2025 Q3 release with archive SHA-256
`7138b2bfabc740a9805b83b3fd0dae28287fc2aab3781a596a741b8fc7861566`.
The loader checks each bundled dictionary and CSV against its reviewed hash,
requires exact ordered headers and counts, and checks key uniqueness and
child-to-parent matches. Unsupported releases require their own contracts.

The five tables and source metadata are inserted in one PostgreSQL transaction.
Any malformed input, duplicate key, unmatched child or changed archive rolls
back the entire load. A repeat of the identical completed load returns its
counts. The source archive remains outside Git and is never modified.

Staging holds each logical CSV value as bytes in column order, together with
the exact CSV header and row number; CSV quoting and record delimiters remain
available in the original archive. Latin-1 is used only as a reversible
byte-to-code-point mapping for the CSV parser, not an assertion of source
encoding. No values are normalized, imputed, classified or published as a
person-quarter analytical dataset. The two ambiguous free-text fields must not
be displayed as decoded text without separate evidence.

After review and migration, invoke the pilot with:

```bash
uv run --locked python -m platform_work_reform.enoe_staging data/enoe/official/2025q3/enoe-2025q3-official.zip
```

The local database backup contains both IMSS and ENOE staging when they reside
in the same database. Back up the original source files separately. This pilot
does not by itself establish eligibility, survey design, weights, representativity
or an analytical population.
