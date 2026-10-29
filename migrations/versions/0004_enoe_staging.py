"""Create source-faithful ENOE staging tables."""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE staging.enoe_load (
          run_id uuid PRIMARY KEY,
          source_file_id uuid NOT NULL,
          reference_period date NOT NULL,
          layout_version text NOT NULL,
          FOREIGN KEY (run_id, source_file_id) REFERENCES meta.ingestion_run(id, source_file_id),
          UNIQUE (source_file_id, reference_period)
        );
        CREATE TABLE staging.enoe_table (
          run_id uuid NOT NULL REFERENCES staging.enoe_load(run_id),
          table_name text NOT NULL CHECK (table_name IN ('VIV','HOG','SDEM','COE1','COE2')),
          header text[] NOT NULL,
          row_count bigint NOT NULL CHECK (row_count > 0),
          member_sha256 text NOT NULL CHECK (member_sha256 ~ '^[0-9a-f]{64}$'),
          dictionary_sha256 text NOT NULL CHECK (dictionary_sha256 ~ '^[0-9a-f]{64}$'),
          PRIMARY KEY (run_id, table_name)
        );
        CREATE TABLE staging.enoe_row (
          run_id uuid NOT NULL,
          table_name text NOT NULL,
          row_number bigint NOT NULL CHECK (row_number > 0),
          source_key text[] NOT NULL,
          raw_fields bytea[] NOT NULL,
          FOREIGN KEY (run_id, table_name) REFERENCES staging.enoe_table(run_id, table_name),
          PRIMARY KEY (run_id, table_name, row_number),
          UNIQUE (run_id, table_name, source_key)
        );
    """)


def downgrade() -> None:
    op.execute(
        "DROP TABLE staging.enoe_row; DROP TABLE staging.enoe_table; DROP TABLE staging.enoe_load;"
    )
