"""App settings, loaded once from the environment (and backend/.env in development).

Required values have no fallback: a missing SECRET_KEY or DATABASE_URL stops the
app at startup instead of silently running with an insecure default.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)


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
