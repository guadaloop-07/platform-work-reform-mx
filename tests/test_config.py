import pytest

from platform_work_reform.config import Settings


def test_project_defaults_and_hidden_password():
    settings = Settings.from_env({"PWR_POSTGRES_PASSWORD": "a-private-test-password"})
    assert settings.database == "platform_work_reform"
    assert settings.host == "127.0.0.1"
    assert settings.port == 55432
    assert "a-private-test-password" not in repr(settings)
    assert settings.connection_parameters()["dbname"] == settings.database


@pytest.mark.parametrize(
    "overrides",
    [
        {"PWR_POSTGRES_PASSWORD": ""},
        {"PWR_POSTGRES_PASSWORD": "  "},
        {"PWR_POSTGRES_PORT": "abc"},
        {"PWR_POSTGRES_PORT": "0"},
        {"PWR_POSTGRES_PORT": "65536"},
        {"PWR_POSTGRES_USER": "bad;user"},
        {"PWR_POSTGRES_DB": "unrelated_project"},
        {"PWR_POSTGRES_HOST": "0.0.0.0"},
    ],
)
def test_reject_invalid_configuration(overrides):
    values = {"PWR_POSTGRES_PASSWORD": "test-secret", **overrides}
    with pytest.raises(ValueError):
        Settings.from_env(values)


def test_unrelated_database_environment_is_not_used():
    with pytest.raises(ValueError, match="PWR_POSTGRES_PASSWORD"):
        Settings.from_env({"DATABASE_URL": "postgresql://other:secret@other/other"})


def test_env_file_and_explicit_environment_precedence(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("PWR_POSTGRES_PASSWORD=from-file\nPWR_POSTGRES_PORT=5437\n")
    monkeypatch.setenv("PWR_POSTGRES_PASSWORD", "from-environment")
    settings = Settings.from_env()
    assert settings.password == "from-environment"
    assert settings.port == 5437
