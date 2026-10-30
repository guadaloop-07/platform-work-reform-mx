# ENOE 2025 Q3 national pilot reconciliation

The `enoe-national-pilot-v1` audit reads one explicit, successful 2025 Q3
staging run for the reviewed archive. It validates the source hash, period,
layout and SDEM header, then streams the person-quarter view under a read-only
repeatable-read snapshot. Raw fields are retained in staging; only aggregate
results are printed. It is not a published analytical dataset, and the source
hash recorded in metadata does not independently revalidate all staged bytes.

```bash
uv run --locked python -m platform_work_reform.enoe_pilot_indicators --run-id <run-uuid>
```

For these national quarterly point estimates, the universe is completed
interviews (`r_def=0`), usual or new residents (`c_res` 1 or 3), and `eda`
15–98. Code 98 is unspecified age for people 12 or older; the official
precoded-variable universe includes this code in the 15-and-over estimates.
Code 99 means unspecified age under 12. Missing age in a completed resident
interview, nonpositive or missing `fac_tri`, and inconsistent `clase1`/`clase2`
in the universe cause failure. Each included record contributes `fac_tri` once.
`clase1=1` identifies PEA; `clase2=1` and `2` identify occupied and unemployed
people respectively. Participation is PEA divided by the 15-plus population;
unemployment is unemployed divided by PEA. Percentages are rounded to one
decimal using decimal half-up rounding. Outside-universe records are counted,
not treated as zero-weight observations in the universe.

These period-specific definitions and codes are documented in INEGI's
[Estructura de la base de datos](https://www.inegi.org.mx/contenidos/programas/enoe/15ymas/doc/enoe_325_fd_c_bas_amp.pdf).
For the reviewed local load on 2026-10-30, 422,306 SDEM rows produced 325,108
in-universe and 97,198 outside-universe rows. Both questionnaire parts matched
346,524 persons; the 75,782 missing each comprised 65,146 under 12 (including
code 99), 9,856 definitive absences and 780 suspended interviews. These are
observed categories, not imputed explanations for questionnaire responses.

| National 2025 Q3 measure | Reproduced | Official reference |
|---|---:|---:|
| Population 15 and older | 103,068,355 | 103,068,355 |
| PEA | 61,303,255 | 61,303,255 |
| Occupied | 59,533,449 | 59,533,449 |
| Unemployed | 1,769,806 | 1,769,806 |
| Participation rate | 59.5% | 59.5% |
| Unemployment rate | 2.9% | 2.9% |

The counts match the [INEGI national quarterly table](https://www.inegi.org.mx/app/tabulados/default.html?nc=603)
and the rates match [boletín 636/25](https://www.inegi.org.mx/contenidos/saladeprensa/boletines/2025/enoe/enoe2025_11.pdf),
table 5. A mismatch makes the command exit unsuccessfully. These checks do not
validate all fields, survey design or precision and do not establish platform
worker identification, cross-quarter identity or causal effects. Variance and
confidence intervals require separately validated survey-design work.
