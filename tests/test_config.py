from backend.bazaario.config import BASE_DIR, _engine_options, _normalize_db_url


def test_relative_sqlite_url_is_resolved_from_project_root():
    assert _normalize_db_url("sqlite:///bazaario.db") == f"sqlite:///{BASE_DIR / 'bazaario.db'}"


def test_absolute_sqlite_url_is_preserved(tmp_path):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    assert _normalize_db_url(url) == url


def test_in_memory_sqlite_url_is_preserved():
    assert _normalize_db_url("sqlite:///:memory:") == "sqlite:///:memory:"


def test_transaction_pooler_disables_prepared_statements():
    url = "postgresql+psycopg://user:secret@pooler.example.com:6543/postgres"
    assert _engine_options(url) == {
        "pool_pre_ping": True,
        "connect_args": {"prepare_threshold": None},
    }


def test_regular_postgres_connection_keeps_default_prepare_behavior():
    url = "postgresql+psycopg://user:secret@db.example.com:5432/postgres"
    assert _engine_options(url) == {"pool_pre_ping": True}


def test_a_configured_jwt_secret_is_not_flagged_as_ephemeral(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "a-real-secret-from-the-environment")
    import importlib

    from backend.bazaario import config as config_module

    reloaded = importlib.reload(config_module)
    try:
        assert reloaded.Config.JWT_SECRET_KEY == "a-real-secret-from-the-environment"
        assert reloaded.Config.JWT_SECRET_KEY_IS_EPHEMERAL is False
    finally:
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        importlib.reload(config_module)


def test_deploying_without_a_jwt_secret_is_refused(monkeypatch):
    """On a multi-instance host a generated key logs users out at random."""
    import pytest

    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.setenv("BAZAARIO_REQUIRE_JWT_SECRET", "1")

    from backend.bazaario import create_app

    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY is not set"):
        create_app({"SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})


def test_local_development_still_boots_without_a_jwt_secret(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("BAZAARIO_REQUIRE_JWT_SECRET", raising=False)

    from backend.bazaario import create_app

    app = create_app({"SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    assert app.config["JWT_SECRET_KEY"]
