"""Create research namespaces and provenance metadata."""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE SCHEMA staging;
        CREATE SCHEMA imss;
        CREATE SCHEMA enoe;
        CREATE SCHEMA reference;
        CREATE SCHEMA analysis;

        CREATE TABLE meta.source_file (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            source_name text NOT NULL CHECK (length(trim(source_name)) > 0),
            original_name text NOT NULL CHECK (length(trim(original_name)) > 0),
            sha256 text NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
            byte_size bigint NOT NULL CHECK (byte_size >= 0),
            source_uri text,
            encoding text,
            registered_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (source_name, sha256)
        );

        CREATE TABLE meta.ingestion_run (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            source_file_id uuid NOT NULL REFERENCES meta.source_file(id),
            status text NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'running', 'succeeded', 'failed')),
            created_at timestamptz NOT NULL DEFAULT now(),
            started_at timestamptz,
            finished_at timestamptz,
            error_summary text,
            UNIQUE (id, source_file_id),
            CHECK ((status IN ('succeeded', 'failed')) = (finished_at IS NOT NULL)),
            CHECK (status <> 'running' OR started_at IS NOT NULL),
            CHECK (finished_at IS NULL OR finished_at >= coalesce(started_at, created_at)),
            CHECK (status = 'failed' OR error_summary IS NULL)
        );
        CREATE INDEX ingestion_run_source_status
            ON meta.ingestion_run(source_file_id, status);

        CREATE TABLE meta.dataset_version (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            dataset_name text NOT NULL CHECK (length(trim(dataset_name)) > 0),
            reference_period date NOT NULL,
            source_file_id uuid NOT NULL REFERENCES meta.source_file(id),
            ingestion_run_id uuid NOT NULL,
            schema_version text NOT NULL CHECK (length(trim(schema_version)) > 0),
            transform_version text NOT NULL CHECK (length(trim(transform_version)) > 0),
            row_count bigint NOT NULL CHECK (row_count >= 0),
            created_at timestamptz NOT NULL DEFAULT now(),
            FOREIGN KEY (ingestion_run_id, source_file_id)
                REFERENCES meta.ingestion_run(id, source_file_id),
            UNIQUE (dataset_name, reference_period, source_file_id,
                    schema_version, transform_version)
        );

        CREATE TABLE meta.quality_check (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            ingestion_run_id uuid NOT NULL REFERENCES meta.ingestion_run(id),
            check_name text NOT NULL CHECK (length(trim(check_name)) > 0),
            passed boolean NOT NULL,
            details jsonb NOT NULL DEFAULT '{}'::jsonb
                CHECK (jsonb_typeof(details) = 'object'),
            checked_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (ingestion_run_id, check_name)
        );
    """)


def downgrade() -> None:
    # Only disposable development databases may use this destructive downgrade.
    op.execute("""
        DROP TABLE meta.quality_check;
        DROP TABLE meta.dataset_version;
        DROP TABLE meta.ingestion_run;
        DROP TABLE meta.source_file;
        DROP SCHEMA analysis;
        DROP SCHEMA reference;
        DROP SCHEMA enoe;
        DROP SCHEMA imss;
        DROP SCHEMA staging;
    """)
