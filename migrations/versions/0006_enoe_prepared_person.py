"""Expose versioned ENOE pilot fields and universe diagnostics."""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE VIEW enoe.prepared_person_2025q3_v1 AS
        WITH source AS (
          SELECT p.run_id, p.source_file_id, p.reference_period, p.source_key,
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
          FROM enoe.person_quarter_pilot p
          JOIN meta.source_file f ON f.id=p.source_file_id
          JOIN staging.enoe_table t ON t.run_id=p.run_id AND t.table_name='SDEM'
          WHERE f.sha256='7138b2bfabc740a9805b83b3fd0dae28287fc2aab3781a596a741b8fc7861566'
            AND encode(sha256(convert_to(array_to_string(t.header, chr(10)), 'UTF8')), 'hex') =
                '13613857a5a025f9ebd57d92e35ca905fb2336855dc6269f3a6bf0951a55fe54'
            AND cardinality(t.header)=115
        ), classified AS (
          SELECT *, CASE
            WHEN r_def IS NULL OR r_def !~ '^[0-9]{1,2}$' THEN 'invalid'
            WHEN r_def <> '0' THEN 'outside_universe'
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
    op.execute("DROP VIEW enoe.prepared_person_2025q3_v1")
