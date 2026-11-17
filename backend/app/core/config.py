"""App settings, loaded once from the environment (and backend/.env in development).

Required values have no fallback: a missing SECRET_KEY or DATABASE_URL stops the
app at startup instead of silently running with an insecure default.

Real environment variables win over backend/.env. That is how the tests point the
app at the test database, and how a server sets its own values in production.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name} (set it in backend/.env)")
    return value


SECRET_KEY = _require("SECRET_KEY")
DB_URL     = _require("DATABASE_URL")
ALGORITHM  = "HS256"

CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
    if o.strip()
]
