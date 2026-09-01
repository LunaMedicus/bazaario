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
