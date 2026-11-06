"""Add reviewed multi-quarter preparation without changing pilot views.

Release hashes and header signatures are frozen here: subsequent registry edits
must not change an already applied migration.
"""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE VIEW enoe.person_quarter_v1 AS
        WITH reviewed(reference_period, layout_version, source_sha256,
                      header_count, header_sha256, completed_code) AS (VALUES
          ('2025-04-01'::date, 'enoe-2025q2-v1',
           '9530a017e3defb0658418b73a47a6039eeb54abf11342fa10693374736515127',
           114, 'f169891401e64a0c2fc9c21f44b8772165ad71787ec521d99f57143465905535', '0'),
          ('2025-07-01'::date, 'enoe-2025q3-v1',
           '7138b2bfabc740a9805b83b3fd0dae28287fc2aab3781a596a741b8fc7861566',
           115, '13613857a5a025f9ebd57d92e35ca905fb2336855dc6269f3a6bf0951a55fe54', '0'),
          ('2025-10-01'::date, 'enoe-2025q4-v1',
           'e4d4284cc9924a40c39544a5530715f320a5627cd81997214c0430827616d9d6',
           115, '13613857a5a025f9ebd57d92e35ca905fb2336855dc6269f3a6bf0951a55fe54', '00'),
          ('2026-04-01'::date, 'enoe-2026q2-v1',
           '9ef8877c363f6097da1a04b2077cbda96300cc474b38f835c4963d1dd8f953df',
           115, '13613857a5a025f9ebd57d92e35ca905fb2336855dc6269f3a6bf0951a55fe54', '0'))
        SELECT v.completed_code, f.sha256 AS source_sha256, l.run_id,
               l.source_file_id, l.reference_period, l.layout_version,
               s.source_key, s.row_number AS sdem_row_number,
               s.raw_fields AS sdem_raw_fields,
               c1.row_number AS coe1_row_number, c1.raw_fields AS coe1_raw_fields,
               c2.row_number AS coe2_row_number, c2.raw_fields AS coe2_raw_fields
        FROM staging.enoe_load l
        JOIN meta.source_file f ON f.id=l.source_file_id
        JOIN reviewed v ON v.reference_period=l.reference_period
          AND v.layout_version=l.layout_version AND v.source_sha256=f.sha256
        JOIN staging.enoe_table t ON t.run_id=l.run_id AND t.table_name='SDEM'
          AND cardinality(t.header)=v.header_count
          AND encode(sha256(convert_to(array_to_string(t.header, chr(10)), 'UTF8')), 'hex')
              =v.header_sha256
        JOIN meta.ingestion_run r ON r.id = l.run_id AND r.status = 'succeeded'
        JOIN staging.enoe_row s ON s.run_id = l.run_id AND s.table_name = 'SDEM'
        LEFT JOIN staging.enoe_row c1 ON c1.run_id = s.run_id
          AND c1.table_name = 'COE1' AND c1.source_key = s.source_key
        LEFT JOIN staging.enoe_row c2 ON c2.run_id = s.run_id
          AND c2.table_name = 'COE2' AND c2.source_key = s.source_key
    """)
    op.execute("""
        CREATE VIEW enoe.prepared_person_v1 AS
        WITH source AS (
          SELECT p.completed_code, p.source_sha256, p.layout_version, p.run_id,
                 p.source_file_id, p.reference_period, p.source_key,
                 p.sdem_row_number, p.coe1_row_number, p.coe2_row_number,
                 trim(encode(p.sdem_raw_fields[array_position(t.header,'eda')], 'escape')) AS eda,
                 trim(encode(p.sdem_raw_fields[array_position(t.header,'r_def')],
                             'escape')) AS r_def,
                 trim(encode(p.sdem_raw_fields[array_position(t.header,'c_res')],
                             'escape')) AS c_res,
                 trim(encode(p.sdem_raw_fields[array_position(t.header,'fac_tri')],
                             'escape')) AS fac_tri,
                 trim(encode(p.sdem_raw_fields[array_position(t.header,'clase1')],
                             'escape')) AS clase1,
                 trim(encode(p.sdem_raw_fields[array_position(t.header,'clase2')],
                             'escape')) AS clase2
          FROM enoe.person_quarter_v1 p
          JOIN staging.enoe_table t ON t.run_id=p.run_id AND t.table_name='SDEM'
        ), classified AS (
          SELECT *, CASE
            WHEN r_def IS NULL OR r_def !~ '^[0-9]{1,2}$' THEN 'invalid'
            WHEN r_def <> completed_code THEN 'outside_universe'
            WHEN c_res = '2' THEN 'outside_universe'
            WHEN c_res IS NULL OR eda IS NULL THEN 'invalid'
            WHEN c_res NOT IN ('1','3') OR eda !~ '^[0-9]{1,2}$' THEN 'invalid'
            WHEN eda::integer < 15 OR eda::integer = 99 THEN 'outside_universe'
            WHEN fac_tri IS NULL OR clase1 IS NULL OR clase2 IS NULL THEN 'invalid'
            WHEN fac_tri !~ '^[0-9]{1,9}$' THEN 'invalid'
            WHEN fac_tri::bigint <= 0 THEN 'invalid'
            WHEN (clase1,clase2) NOT IN (('1','1'),('1','2'),('2','3'),('2','4'))
              THEN 'invalid'
            ELSE 'eligible' END AS preparation_status
          FROM source
        )
        SELECT *, CASE WHEN preparation_status='eligible' THEN fac_tri::bigint
                       END AS quarterly_weight
        FROM classified
        """)


def downgrade() -> None:
    op.execute("DROP VIEW enoe.prepared_person_v1")
    op.execute("DROP VIEW enoe.person_quarter_v1")
