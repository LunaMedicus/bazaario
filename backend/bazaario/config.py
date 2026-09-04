from pathlib import Path
import os
import secrets
from urllib.parse import urlsplit


BASE_DIR = Path(__file__).resolve().parents[2]


def _normalize_db_url(url: str) -> str:
    if not url:
        return f"sqlite:///{BASE_DIR / 'bazaario.db'}"
    if url == "sqlite:///:memory:":
        return url
    if url.startswith("sqlite:///") and not url.startswith("sqlite:////"):
        relative_path = url.removeprefix("sqlite:///")
        return f"sqlite:///{BASE_DIR / relative_path}"
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://") and not url.startswith("postgresql+"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def _engine_options(url: str) -> dict:
    options = {"pool_pre_ping": True}
    if url.startswith("postgresql+") and urlsplit(url).port == 6543:
        options["connect_args"] = {"prepare_threshold": None}
    return options


def _on_a_multi_instance_host() -> bool:
    """True when more than one process may serve the same users.

    A per-process secret is survivable on a laptop and broken anywhere that
    runs several instances: each one signs with a different key, so a token
    minted by instance A is rejected as invalid by instance B and the user is
    logged out at random. Vercel sets VERCEL; the override exists so any other
    host can demand the same guarantee.
    """
    return bool(os.getenv("VERCEL") or os.getenv("BAZAARIO_REQUIRE_JWT_SECRET"))


class Config:
    SQLALCHEMY_DATABASE_URI = _normalize_db_url(os.getenv("DATABASE_URL", ""))
    SQLALCHEMY_ENGINE_OPTIONS = _engine_options(SQLALCHEMY_DATABASE_URI)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # A generated fallback keeps a fresh clone runnable with no .env; the
    # flag beside it lets create_app refuse that fallback where it is unsafe.
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY") or secrets.token_urlsafe(48)
    JWT_SECRET_KEY_IS_EPHEMERAL = not os.getenv("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", "86400"))
    JSON_SORT_KEYS = False
    CORS_ORIGINS = os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    )
