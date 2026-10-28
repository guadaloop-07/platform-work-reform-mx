import os
import uuid
from dataclasses import replace

import psycopg
import pytest
from psycopg import sql

from platform_work_reform.config import Settings
from platform_work_reform.migrate import upgrade


@pytest.fixture
def isolated_database():
    if os.environ.get("PWR_RUN_DB_TESTS") != "1":
        pytest.skip("Use just db-test to enable isolated database integration tests")
    settings = Settings.from_env()
    name = "platform_work_reform_test_" + uuid.uuid4().hex
    isolated = replace(settings, database=name)
    with psycopg.connect(**settings.connection_parameters("postgres"), autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(name)))
    try:
        upgrade(isolated)
        yield isolated
    finally:
        with psycopg.connect(
            **settings.connection_parameters("postgres"), autocommit=True
        ) as admin:
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
