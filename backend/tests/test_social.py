"""Follows: public vs private accounts, requests, unfollow, search."""
from helpers import follow


def test_follow_public_account_is_instant(client, alice, bob):
    assert follow(client, alice, bob)["status"] == "accepted"
    friends = client.get("/friends", headers=alice.headers).json()
    assert [f["email"] for f in friends] == [bob.email]


def test_follow_is_one_directional(client, alice, bob):
    follow(client, alice, bob)
    assert client.get("/friends", headers=bob.headers).json() == []


def test_follow_private_account_needs_approval(client, alice, make_user):
    priv = make_user("priv", private=True)
    assert follow(client, alice, priv)["status"] == "pending"
    assert client.get("/friends", headers=alice.headers).json() == []

    pending = client.get("/friends/requests/pending", headers=priv.headers).json()
    assert [p["requester_email"] for p in pending] == [alice.email]

    r = client.patch(f"/friends/requests/{pending[0]['id']}", json={"action": "accept"}, headers=priv.headers)
    assert r.status_code == 200 and r.json()["status"] == "accepted"
    assert [f["email"] for f in client.get("/friends", headers=alice.headers).json()] == [priv.email]


def test_declined_request_can_be_sent_again(client, alice, make_user):
    priv = make_user("priv", private=True)
    req = follow(client, alice, priv)
    client.patch(f"/friends/requests/{req['id']}", json={"action": "decline"}, headers=priv.headers)
    assert follow(client, alice, priv)["status"] == "pending"


def test_only_the_addressee_can_answer_a_request(client, alice, bob, make_user):
    priv = make_user("priv", private=True)
    req = follow(client, alice, priv)
    r = client.patch(f"/friends/requests/{req['id']}", json={"action": "accept"}, headers=bob.headers)
    assert r.status_code == 404
    r = client.patch(f"/friends/requests/{req['id']}", json={"action": "accept"}, headers=alice.headers)
    assert r.status_code == 404


def test_bad_request_action(client, alice, make_user):
    priv = make_user("priv", private=True)
    req = follow(client, alice, priv)
    r = client.patch(f"/friends/requests/{req['id']}", json={"action": "maybe"}, headers=priv.headers)
    assert r.status_code == 400


def test_cannot_follow_yourself(client, alice):
    r = client.post("/friends/request", json={"addressee_email": alice.email}, headers=alice.headers)
    assert r.status_code == 400


def test_cannot_follow_unknown_user(client, alice):
    r = client.post("/friends/request", json={"addressee_email": "ghost@test.com"}, headers=alice.headers)
    assert r.status_code == 404


def test_duplicate_follow_and_duplicate_request(client, alice, bob, make_user):
    follow(client, alice, bob)
    r = client.post("/friends/request", json={"addressee_email": bob.email}, headers=alice.headers)
    assert r.status_code == 409

    priv = make_user("priv", private=True)
    follow(client, alice, priv)
    r = client.post("/friends/request", json={"addressee_email": priv.email}, headers=alice.headers)
    assert r.status_code == 409


def test_unfollow_removes_only_my_direction(client, alice, bob):
    follow(client, alice, bob)
    follow(client, bob, alice)
    assert client.delete(f"/follow/{bob.email}", headers=alice.headers).status_code == 204
    assert client.get("/friends", headers=alice.headers).json() == []
    assert [f["email"] for f in client.get("/friends", headers=bob.headers).json()] == [alice.email]


def test_user_search_shows_my_follow_status(client, alice, bob, make_user):
    priv = make_user("priv", private=True)
    make_user("carol")
    follow(client, alice, bob)
    follow(client, alice, priv)

    results = {u["email"]: u for u in client.get("/users/search?q=", headers=alice.headers).json()}
    assert alice.email not in results                      # never yourself
    assert results[bob.email]["friendship_status"] == "following"
    assert results[priv.email]["friendship_status"] == "pending_sent"
    assert results[priv.email]["is_private"] is True
    assert results["carol@test.com"]["friendship_status"] is None


def test_user_search_filters(client, alice, make_user):
    make_user("bobby")
    make_user("carol")
    emails = [u["email"] for u in client.get("/users/search?q=bob", headers=alice.headers).json()]
    assert emails == ["bobby@test.com"]


def test_someone_elses_following_list(client, alice, bob, carol):
    follow(client, bob, carol)
    r = client.get(f"/users/{bob.email}/friends", headers=alice.headers)
    assert [f["email"] for f in r.json()] == [carol.email]
    assert client.get("/users/ghost@test.com/friends", headers=alice.headers).status_code == 404
