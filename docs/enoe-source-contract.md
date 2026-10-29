# ENOE source and join contract: 2025 third-quarter pilot

This is a preliminary key contract for the national 2025 third-quarter ENOE
files, not a complete CSV schema or authorization to ingest them. INEGI's
[Estructura de la base de datos](https://www.inegi.org.mx/contenidos/programas/enoe/15ymas/doc/enoe_325_fd_c_bas_amp.pdf)
describes five tables and the relationship fields. It specifies `ENT` through
2025 Q2 and `CVE_ENT` starting in 2025 Q3; the 2025 Q3 dictionaries also use
`CVE_ENT`. This contract uses the latter spelling and does not silently rename
fields in source files.

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

`enoe_contract` checks required key names and distinct, nonblank string keys;
it can count joins after callers verify the table relationship and period. It
does not validate complete headers, data types, source encoding, values,
eligibility or statistical outputs. It fails closed for unreviewed periods.
The checks are synthetic and do not establish that an official release passes.

Before P15 ingestion, obtain the official archives and dictionaries, record
origin, retrieval date, archive/member hashes and release revisions, inspect
actual headers, encoding and row counts, reconcile the keys and exceptions,
and define complete version-specific layouts and transactional load rules.
INEGI can revise releases, so a new hash is a new version. P16 must document
population, weights, missingness and the resulting row counts. Within-quarter
keys do not establish cross-quarter person identity, nor any individual linkage
to aggregate IMSS records. Platform-worker identification and causal design are
separate feasibility work.
