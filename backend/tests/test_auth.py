"""Signup, login, tokens, password change/reset and the privacy setting."""
import jwt
import pytest

from app.core.security import create_reset_token


def test_signup_then_login(client):
    r = client.post("/signup", json={"email": "new@test.com", "password": "secret123"})
    assert r.status_code == 201
    r = client.post("/login", json={"email": "new@test.com", "password": "secret123"})
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "new@test.com"
    assert jwt.decode(body["token"], options={"verify_signature": False})["sub"] == "new@test.com"


def test_password_is_stored_hashed(client, db):
    client.post("/signup", json={"email": "new@test.com", "password": "secret123"})
    db.execute("SELECT hashed_password FROM users WHERE email = 'new@test.com'")
    stored = db.fetchone()[0]
    assert stored != "secret123" and stored.startswith("$2")


def test_signup_duplicate_email(client, alice):
    r = client.post("/signup", json={"email": alice.email, "password": "whatever1"})
    assert r.status_code == 400


def test_signup_rejects_short_password(client):
    r = client.post("/signup", json={"email": "x@test.com", "password": "12345"})
    assert r.status_code == 400


def test_signup_rejects_invalid_email(client):
    r = client.post("/signup", json={"email": "not-an-email", "password": "secret123"})
    assert r.status_code == 422


@pytest.mark.parametrize("email,password", [
    ("alice@test.com", "wrong-password"),
    ("nobody@test.com", "secret123"),
])
def test_login_failures_look_the_same(client, alice, email, password):
    r = client.post("/login", json={"email": email, "password": password})
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid email or password"


def test_protected_endpoint_needs_a_token(client):
    assert client.get("/me").status_code == 403   # HTTPBearer: no header at all


def test_garbage_token_is_rejected(client):
    r = client.get("/me", headers={"Authorization": "Bearer not.a.token"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid token"


def test_expired_token_is_rejected(client, alice):
    expired = jwt.encode({"sub": alice.email, "exp": 1}, "test-secret-key-not-used-anywhere-else",
                         algorithm="HS256")
    r = client.get("/me", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Token expired"


def test_token_signed_with_another_key_is_rejected(client, alice):
    forged = jwt.encode({"sub": alice.email}, "some-other-key", algorithm="HS256")
    r = client.get("/me", headers={"Authorization": f"Bearer {forged}"})
    assert r.status_code == 401


def test_me(client, alice):
    r = client.get("/me", headers=alice.headers)
    assert r.json() == {"email": alice.email, "is_private": False}


def test_privacy_toggle(client, alice):
    r = client.patch("/me/privacy", json={"is_private": True}, headers=alice.headers)
    assert r.json() == {"is_private": True}
    assert client.get("/me", headers=alice.headers).json()["is_private"] is True


class TestChangePassword:
    def test_success(self, client, alice):
        r = client.post("/change-password", headers=alice.headers,
                        json={"current_password": alice.password, "new_password": "newpass123"})
        assert r.status_code == 200
        assert client.post("/login", json={"email": alice.email, "password": "newpass123"}).status_code == 200
        assert client.post("/login", json={"email": alice.email, "password": alice.password}).status_code == 401

    def test_wrong_current_password(self, client, alice):
        r = client.post("/change-password", headers=alice.headers,
                        json={"current_password": "nope", "new_password": "newpass123"})
        assert r.status_code == 400

    def test_new_password_too_short(self, client, alice):
        r = client.post("/change-password", headers=alice.headers,
                        json={"current_password": alice.password, "new_password": "123"})
        assert r.status_code == 400


class TestPasswordReset:
    @pytest.fixture
    def outbox(self, monkeypatch):
        sent = []
        monkeypatch.setattr("app.routers.auth.send_reset_email", lambda to, link: sent.append((to, link)))
        return sent

    def test_full_flow(self, client, alice, outbox):
        r = client.post("/forgot-password", json={"email": alice.email})
        assert r.status_code == 200
        assert len(outbox) == 1 and outbox[0][0] == alice.email
        token = outbox[0][1].split("token=")[1]

        r = client.post("/reset-password", json={"token": token, "new_password": "brandnew1"})
        assert r.status_code == 200
        assert client.post("/login", json={"email": alice.email, "password": "brandnew1"}).status_code == 200

    def test_unknown_email_gets_same_answer_but_no_email(self, client, alice, outbox):
        known = client.post("/forgot-password", json={"email": alice.email}).json()
        unknown = client.post("/forgot-password", json={"email": "ghost@test.com"}).json()
        assert known == unknown
        assert [to for to, _ in outbox] == [alice.email]

    def test_reset_token_cannot_log_in(self, client, alice):
        token = create_reset_token(alice.email)
        r = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401

    def test_login_token_cannot_reset_password(self, client, alice):
        login_token = alice.headers["Authorization"].split()[1]
        r = client.post("/reset-password", json={"token": login_token, "new_password": "hijacked1"})
        assert r.status_code == 400

    def test_garbage_token(self, client):
        r = client.post("/reset-password", json={"token": "junk", "new_password": "whatever1"})
        assert r.status_code == 400

    def test_short_password(self, client, alice):
        r = client.post("/reset-password",
                        json={"token": create_reset_token(alice.email), "new_password": "123"})
        assert r.status_code == 400
