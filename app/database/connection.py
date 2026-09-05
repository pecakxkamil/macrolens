"""PostgreSQL connection helpers for MacroLens."""

import os

import psycopg
from dotenv import load_dotenv


REQUIRED_ENV_VARS = (
    "DB_HOST",
    "DB_PORT",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
)


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_connection() -> psycopg.Connection:
    """Create a PostgreSQL connection from environment configuration."""
    load_dotenv()

    missing = [name for name in REQUIRED_ENV_VARS if not os.getenv(name)]
    if missing:
        names = ", ".join(missing)
        raise RuntimeError(f"Missing required environment variables: {names}")

    return psycopg.connect(
        host=_get_required_env("DB_HOST"),
        port=int(_get_required_env("DB_PORT")),
        dbname=_get_required_env("DB_NAME"),
        user=_get_required_env("DB_USER"),
        password=_get_required_env("DB_PASSWORD"),
    )
