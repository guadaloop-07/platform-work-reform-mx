# ENOE source and join contract: 2025 third-quarter pilot

This contract covers source-faithful staging of the reviewed national ENOE
2025 Q3 release. It does not authorize publication of analytical estimates. INEGI's
[Estructura de la base de datos](https://www.inegi.org.mx/contenidos/programas/enoe/15ymas/doc/enoe_325_fd_c_bas_amp.pdf)
describes five tables and the relationship fields. It specifies `ENT` through
2025 Q2 and `CVE_ENT` starting in 2025 Q3; the 2025 Q3 dictionaries also use
`CVE_ENT`. The official CSV header uses lowercase names (`cve_ent`, etc.);
the code uses those exact names and does not silently rename source fields.

| Table | Grain | Within-quarter key |
|---|---|---|
| VIV | dwelling | `TIPO`, `MES_CAL`, `CD_A`, `CVE_ENT`, `CON`, `V_SEL` |
| HOG | household | dwelling key, `N_HOG`, `H_MUD` |
| SDEM | household member | household key, `N_REN` |
| COE1, COE2 | person questionnaire part | household key, `N_REN` |

The table dictionaries are [VIV](https://www.inegi.org.mx/rnm/index.php/catalog/1121/data-dictionary/F46?file_name=VIVT325),
[HOG](https://www.inegi.org.mx/rnm/index.php/catalog/1121/data-dictionary/F45?file_name=HOGT325),
[SDEM](https://www.inegi.org.mx/rnm/index.php/catalog/1121/data-dictionary/F47),
[COE1](https://www.inegi.org.mx/rnm/index.php/catalog/1121/data-dictionary/F48?file_name=COE1T325), and
[COE2](https://www.inegi.org.mx/rnm/index.php/catalog/1121/data-dictionary/F49?file_name=COE2T325).
The diagram adds `TIPO` and `MES_CAL` beginning in 2020 Q3; this does not
establish a complete contract for other periods. Quarter and source version
must be explicit dataset metadata, never inferred from these keys alone.

SDEM covers household members; the two COE parts concern the eligible
questionnaire population, not every SDEM row. Preserve all SDEM rows in a
person-quarter preparation and report unmatched records in both directions;
do not interpret every missing COE as a data error or replace it with zero.
Before publication, establish the exact period-specific eligibility and
nonresponse rules from the official documentation and inspect observed
exceptions. Join at the relevant parent key, requiring uniqueness at each
source grain and separately reporting orphan children and parents without
children. COE1 and COE2 match on the full person key. No join may cross periods
or source releases implicitly.

Preserve original bytes, all columns, leading zeros, blank values and coded
missing values. Do not convert missing values to zero or assign a universal
meaning to blank responses: definitions and questionnaire skips are variable-
and version-specific. `FAC_TRI` and `FAC_MEN` are respectively quarterly and
monthly expansion factors in the official structure; retain them and the
design variables, and select the appropriate weight and survey design for each
estimate. Do not sum weights across joins that multiply persons. Municipal
identifiers do not establish municipal representativeness.

For 2025 Q3, `cs_p21_des` and `cs_p23_des` describe other reasons for a
household member's departure or arrival. Their source bytes include values
whose text encoding remains unresolved. For the pilot, retain the complete
original archive and CSV bytes and store the two logical CSV field values as
bytes, linked to their source row. A strict Latin-1 parse is a reversible byte
mapping, not a declaration of the text encoding; recover field bytes without
publishing decoded text or replacing characters. CSV quoting and delimiters
are preserved by the original file, not by the extracted field values. Empty
bytes remain empty, without interpreting the survey's missing-value meaning.
Any later text interpretation requires separate evidence and provenance.

`enoe_contract` checks exact ordered headers using SHA-256 of the ASCII field
names joined by newline, required key names and distinct, nonblank keys. Join
counts require the same period and release and an explicitly supported table
relationship. It also recovers the two text values from a byte-preserving
Latin-1 parse. It does not interpret data types, missing codes, survey universe
or statistical outputs. Unknown periods and headers fail closed.

For P15 ingestion, record origin, retrieval date, archive/member hashes and
release revisions; enforce actual headers, row counts, keys and exceptions;
and use a transactional load preserving all raw fields. The
initial 2025 Q3 archive and dictionaries have been inspected as documented in
`enoe-2025q3-source-audit.md`; this does not establish contracts for other
quarters.
INEGI can revise releases, so a new hash is a new version requiring review.

## Requirements before analysis

For the precoded variables, the 2025 structure specifies `r_def=0`,
`c_res` in `1` or `3`, and the 15-and-older age universe, including the
unspecified-adult code `eda=98`. The value `eda=99` means an unspecified age
under 12, and `eda=97` represents 97 or more; neither is a literal age.
Apply the official variable-specific universe and skip rules, not this criterion
indiscriminately to all questions. Use quarterly `fac_tri` for appropriate
quarterly estimates and retain design variables; justify the population and
survey design for each estimate. Document coded missingness, nonresponse,
weight use and reconciliation with published aggregates before releasing
person-quarter results. P16 must document the resulting row counts. Within-quarter
keys do not establish cross-quarter person identity, nor any individual linkage
to aggregate IMSS records. Platform-worker identification and causal design are
separate feasibility work.
