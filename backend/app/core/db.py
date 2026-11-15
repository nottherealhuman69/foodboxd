"""Database connection dependency."""
import psycopg2
from psycopg2.extras import RealDictCursor

from app.core.config import DB_URL


def get_db():
    conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()
