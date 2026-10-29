# ENOE 2025 Q3 source audit

On 2026-10-29, the official INEGI release
[Encuesta Nacional de Ocupación y Empleo 2025, Cuestionario básico, datos correspondientes al tercer trimestre](https://www.inegi.org.mx/app/descarga/ficha.html?ag=0&f=csv&tit=3161259)
was retrieved from the [published CSV archive](https://www.inegi.org.mx/contenidos/programas/enoe/15ymas/datosabiertos/2025/conjunto_de_datos_enoe_2025_3t_csv.zip).
The release identifier is `MEX-INEGI.ESD3.03-ENOE-2025-III`, last modified
2025-11-26 according to the official download metadata. The untouched archive
is outside Git under `data/enoe/official/2025q3/` and has SHA-256
`7138b2bfabc740a9805b83b3fd0dae28287fc2aab3781a596a741b8fc7861566`.
This is a checksum of the retrieved copy, not an independently published checksum.

| Table | Rows | Columns | CSV SHA-256 |
|---|---:|---:|---|
| VIV | 150,405 | 26 | `c3e11e1b0d5e5b30f5763022c803e2e26667a97acd74b1a64aa3e8d1f837b327` |
| HOG | 151,354 | 38 | `dfacd7dcc594f5a09a869fa571154529a3efb432b94b4b865a4675094dbf7b84` |
| SDEM | 422,306 | 115 | `04bd5d5f9668848ac6c435f29abe3b20e6693f02f2ee880a1e9dc0aab1c94c9d` |
| COE1 | 346,524 | 174 | `aafec7839128b296bded5b4160e73f251ccc807b8f863731d8258f9206fe1ae2` |
| COE2 | 346,524 | 84 | `66bae80c474b5c4ae0d855afb96c69593c053ba694b6caa6cf770c492ce1585b` |

The five source headers exactly match the ordered `NEMÓNICO` values in their
respective bundled dictionaries. Their observed CSV names are lowercase. CSV
parsing with strict CP1252 decoding encountered no malformed field counts;
all documented key fields were present, nonblank and unique. Strict UTF-8
decoding fails for SDEM but succeeds for the other four data files; CP1252
decodes all five. This is evidence, not proof of the intended source encoding.
The bundled dictionaries decode as UTF-8. Review the ambiguous text and source
metadata before selecting a text interpretation; never replace invalid bytes.
The only non-ASCII bytes in SDEM occur in `cs_p21_des` (376 rows) and
`cs_p23_des` (84 rows); under CP1252 the non-ASCII characters are U+00CB and
U+00D0. Their interpretation is not established by decoding alone. Do not
publish normalized text or claim that CP1252 is the authoritative encoding.
The source contract retains those two logical field values as bytes using a
reversible Latin-1 parse, while preserving the original archive and CSV bytes.

| Relationship | Child rows with parent | Child rows without parent | Parent rows without child |
|---|---:|---:|---:|
| VIV → HOG | 151,354 | 0 | 0 |
| HOG → SDEM | 422,306 | 0 | 25,922 |
| SDEM → COE1 | 346,524 | 0 | 75,782 |
| SDEM → COE2 | 346,524 | 0 | 75,782 |
| COE1 → COE2 | 346,524 | 0 | 0 |

The 75,782 SDEM records without COE1 include 65,146 classified as under 12,
including 33 whose `eda=99` indicates an unspecified age in that age group.
The remaining 10,636 comprise 9,856 with `r_def=0`, `c_res=2` (definitively
absent) and 780 with `r_def=15` (suspended interview). The published
[2025 structure](https://www.inegi.org.mx/contenidos/programas/enoe/15ymas/doc/enoe_325_fd_c_bas_amp.pdf)
defines `eda=98` as unspecified age for people 12 and older; neither 98 nor 99
should be interpreted as an actual age. These categories explain the observed
pattern, but should not be used to impute questionnaire responses.

The 25,922 HOG records without SDEM have nonzero `r_def` codes associated with
non-interviews. The bundled `r_def` catalog omits values 17 and 18, although
the 2025 structure documents them as telephone-specific non-interview codes;
588 affected households use one of these values. Do not enforce the incomplete
catalog as an exhaustive allowlist.

To reproduce the hash, layout, key, and unmatched-category audit with the
unchanged archive at the path above, run:

```bash
python scripts/audit_enoe_2025q3.py
```

This audit establishes header and key behavior for this archive only. It does
not validate every value, type, weight, survey universe or statistical result,
nor does it build or load a person-quarter dataset. Validate those in P15/P16,
including missingness and the unexplained exceptions, before publication.
