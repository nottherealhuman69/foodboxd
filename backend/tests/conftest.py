"""Shared test setup.

- Points the app at TEST_DATABASE_URL (and refuses anything that isn't on this machine).
- Builds the schema with the real Alembic migrations once per run.
- Empties every table before each test, so tests never depend on each other.
- Provides `client` (talks to the app in-process, no server needed) and `make_user`.
"""
import functools
import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from dotenv import dotenv_values

BACKEND = Path(__file__).resolve().parents[1]

# ── 1. Choose the database BEFORE the app is imported ─────────────────────────
TEST_URL = os.getenv("TEST_DATABASE_URL") or dotenv_values(BACKEND / ".env").get("TEST_DATABASE_URL")
if not TEST_URL:
    pytest.exit("TEST_DATABASE_URL is not set (add it to backend/.env).", returncode=2)
if urlsplit(TEST_URL).hostname not in ("localhost", "127.0.0.1", "::1"):
    # Tests delete every row before each test: never let them near a real database.
    pytest.exit("Refusing to run: TEST_DATABASE_URL must point at localhost.", returncode=2)

os.environ["DATABASE_URL"] = TEST_URL
os.environ["SECRET_KEY"] = "test-secret-key-not-used-anywhere-else"
os.environ["SMTP_USER"] = ""   # never send real email from tests
os.environ["SMTP_PASS"] = ""

import bcrypt  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
import psycopg2  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core import config as app_config  # noqa: E402
from app.main import app  # noqa: E402

assert app_config.DB_URL == TEST_URL, "app is not using the test database"

# bcrypt's default cost is deliberately slow; tests hash hundreds of passwords.
bcrypt.gensalt = functools.partial(bcrypt.gensalt, rounds=4)


# ── 2. Schema: run the real migrations once per test run ─────────────────────
@pytest.fixture(scope="session", autouse=True)
def migrated_db():
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.attributes["url"] = TEST_URL
    cfg.attributes["configure_logger"] = False
    command.downgrade(cfg, "base")   # start from nothing, so the migrations are tested too
    command.upgrade(cfg, "head")
    with psycopg2.connect(TEST_URL) as conn, conn.cursor() as cur:
        cur.execute("""SELECT tablename FROM pg_tables
                       WHERE schemaname = 'public' AND tablename <> 'alembic_version'""")
        tables = [r[0] for r in cur.fetchall()]
    conn.close()
    return tables


# ── 3. Empty every table before each test ────────────────────────────────────
@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    with psycopg2.connect(TEST_URL) as conn, conn.cursor() as cur:
        cur.execute(f"TRUNCATE {', '.join(migrated_db)} RESTART IDENTITY CASCADE")
    conn.close()


@pytest.fixture
def db():
    """A direct connection, for checking what an endpoint actually wrote."""
    conn = psycopg2.connect(TEST_URL)
    conn.autocommit = True
    yield conn.cursor()
    conn.close()


# ── 4. Talking to the app ────────────────────────────────────────────────────
@pytest.fixture
def client():
    # raise_server_exceptions=False: a crash comes back as a 500, like it would for the app
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


class User:
    def __init__(self, email, token, password):
        self.email = email
        self.password = password
        self.headers = {"Authorization": f"Bearer {token}"}
        self.username = email.split("@")[0]

    def __repr__(self):
        return f"<User {self.email}>"


@pytest.fixture
def make_user(client):
    """make_user('alice') -> a signed-up, logged-in User (alice@test.com)."""
    def _make(name, private=False, password="secret123"):
        email = f"{name}@test.com"
        r = client.post("/signup", json={"email": email, "password": password})
        assert r.status_code == 201, r.text
        r = client.post("/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.text
        user = User(email, r.json()["token"], password)
        if private:
            r = client.patch("/me/privacy", json={"is_private": True}, headers=user.headers)
            assert r.status_code == 200, r.text
        return user
    return _make


@pytest.fixture
def alice(make_user):
    return make_user("alice")


@pytest.fixture
def bob(make_user):
    return make_user("bob")


@pytest.fixture
def carol(make_user):
    return make_user("carol")
