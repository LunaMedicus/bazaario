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


class Config:
    SQLALCHEMY_DATABASE_URI = _normalize_db_url(os.getenv("DATABASE_URL", ""))
    SQLALCHEMY_ENGINE_OPTIONS = _engine_options(SQLALCHEMY_DATABASE_URI)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY") or secrets.token_urlsafe(48)
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", "86400"))
    JSON_SORT_KEYS = False
    CORS_ORIGINS = os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    )
