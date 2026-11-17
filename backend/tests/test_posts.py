"""Companion tags, reposts and forks."""
from helpers import follow, meal, review


class TestTags:
    def test_can_only_tag_people_you_follow(self, client, alice, bob, carol):
        follow(client, alice, bob)
        r = review(client, alice, tagged_emails=[bob.email, carol.email, alice.email])
        assert [t["email"] for t in r["tagged"]] == [bob.email]

    def test_editing_removes_tag_and_that_persons_repost(self, client, alice, bob, db):
        follow(client, alice, bob)
        r = review(client, alice, tagged_emails=[bob.email])
        client.post(f"/posts/review/{r['id']}/repost", headers=bob.headers)
        upd = client.patch(f"/reviews/{r['id']}", headers=alice.headers,
                           json={"dish_name": "Ramen", "type": "restaurant", "restaurant_name": "Ichiran",
                                 "rating": 4, "tagged_emails": []})
        assert upd.json()["tagged"] == []
        db.execute("SELECT count(*) FROM post_reposts")
        assert db.fetchone()[0] == 0

    def test_meal_tags(self, client, alice, bob):
        follow(client, alice, bob)
        m = meal(client, alice, tagged_emails=[bob.email])
        assert [t["email"] for t in m["tagged"]] == [bob.email]

    def test_deleting_a_post_removes_tags_and_reposts(self, client, alice, bob, db):
        follow(client, alice, bob)
        r = review(client, alice, tagged_emails=[bob.email])
        client.post(f"/posts/review/{r['id']}/repost", headers=bob.headers)
        client.delete(f"/reviews/{r['id']}", headers=alice.headers)
        db.execute("SELECT (SELECT count(*) FROM post_tags) + (SELECT count(*) FROM post_reposts)")
        assert db.fetchone()[0] == 0


class TestReposts:
    def test_only_tagged_people_can_repost(self, client, alice, bob):
        r = review(client, alice)
        assert client.post(f"/posts/review/{r['id']}/repost", headers=bob.headers).status_code == 403

    def test_repost_toggles_and_shows_on_profile(self, client, alice, bob, carol):
        follow(client, alice, bob)
        r = review(client, alice, tagged_emails=[bob.email])
        assert client.post(f"/posts/review/{r['id']}/repost", headers=bob.headers).json() == {"reposted": True}

        mine = client.get("/reviews", headers=bob.headers).json()
        assert mine[0]["id"] == r["id"] and mine[0]["reposted_by"]["email"] == bob.email
        on_profile = client.get(f"/users/{bob.email}/reviews", headers=carol.headers).json()
        assert [x["id"] for x in on_profile] == [r["id"]]
        assert client.get(f"/reviews/{r['id']}/detail", headers=bob.headers).json()["user_reposted"] is True

        assert client.post(f"/posts/review/{r['id']}/repost", headers=bob.headers).json() == {"reposted": False}
        assert client.get("/reviews", headers=bob.headers).json() == []

    def test_meal_repost(self, client, alice, bob):
        # regression: reposting a meal used to always crash (500)
        follow(client, alice, bob)
        m = meal(client, alice, tagged_emails=[bob.email])
        assert client.post(f"/posts/meal/{m['id']}/repost", headers=bob.headers).json() == {"reposted": True}
        assert [x["id"] for x in client.get("/meals", headers=bob.headers).json()] == [m["id"]]
        assert client.post(f"/posts/meal/{m['id']}/repost", headers=bob.headers).json() == {"reposted": False}

    def test_meal_repost_needs_a_tag(self, client, alice, bob):
        m = meal(client, alice)
        assert client.post(f"/posts/meal/{m['id']}/repost", headers=bob.headers).status_code == 403

    def test_cannot_repost_what_you_forked(self, client, alice, bob):
        # regression: reviews used to skip this check
        follow(client, alice, bob)
        r = review(client, alice, tagged_emails=[bob.email])
        m = meal(client, alice, tagged_emails=[bob.email])
        review(client, bob, forked_from_id=r["id"])
        meal(client, bob, forked_from_id=m["id"])
        assert client.post(f"/posts/review/{r['id']}/repost", headers=bob.headers).status_code == 409
        assert client.post(f"/posts/meal/{m['id']}/repost", headers=bob.headers).status_code == 409

    def test_bad_post_type_and_missing_post(self, client, alice):
        assert client.post("/posts/pizza/1/repost", headers=alice.headers).status_code == 400
        assert client.post("/posts/review/999/repost", headers=alice.headers).status_code == 404


class TestForks:
    def test_fork_a_review_you_are_tagged_in(self, client, alice, bob):
        follow(client, alice, bob)
        original = review(client, alice, tagged_emails=[bob.email])
        fork = review(client, bob, forked_from_id=original["id"], rating=3)
        assert fork["forked_from_id"] == original["id"]

        detail = client.get(f"/reviews/{fork['id']}/detail", headers=bob.headers).json()
        assert detail["forked_from"]["id"] == original["id"]
        assert detail["forked_from"]["user_email"] == alice.email
        orig_detail = client.get(f"/reviews/{original['id']}/detail", headers=bob.headers).json()
        assert orig_detail["my_fork"] == {"kind": "review", "id": fork["id"]}

    def test_cannot_fork_without_being_tagged(self, client, alice, bob):
        original = review(client, alice)
        r = client.post("/reviews", headers=bob.headers, json={
            "dish_name": "Ramen", "type": "restaurant", "rating": 3, "forked_from_id": original["id"]})
        assert r.status_code == 403

    def test_cannot_fork_twice(self, client, alice, bob):
        follow(client, alice, bob)
        original = review(client, alice, tagged_emails=[bob.email])
        review(client, bob, forked_from_id=original["id"])
        r = client.post("/reviews", headers=bob.headers, json={
            "dish_name": "Ramen", "type": "restaurant", "rating": 3, "forked_from_id": original["id"]})
        assert r.status_code == 409

    def test_cannot_fork_after_reposting(self, client, alice, bob):
        follow(client, alice, bob)
        original = review(client, alice, tagged_emails=[bob.email])
        client.post(f"/posts/review/{original['id']}/repost", headers=bob.headers)
        r = client.post("/reviews", headers=bob.headers, json={
            "dish_name": "Ramen", "type": "restaurant", "rating": 3, "forked_from_id": original["id"]})
        assert r.status_code == 409

    def test_fork_of_missing_post(self, client, alice):
        r = client.post("/reviews", headers=alice.headers, json={
            "dish_name": "Ramen", "type": "restaurant", "rating": 3, "forked_from_id": 999})
        assert r.status_code == 404

    def test_fork_a_meal(self, client, alice, bob):
        follow(client, alice, bob)
        original = meal(client, alice, tagged_emails=[bob.email])
        fork = meal(client, bob, forked_from_id=original["id"])
        assert fork["forked_from_id"] == original["id"]
        assert client.get(f"/meals/{original['id']}/detail", headers=bob.headers).json()["my_fork"]["id"] == fork["id"]

    def test_deleting_the_original_keeps_the_fork(self, client, alice, bob):
        follow(client, alice, bob)
        original = review(client, alice, tagged_emails=[bob.email])
        fork = review(client, bob, forked_from_id=original["id"])
        client.delete(f"/reviews/{original['id']}", headers=alice.headers)
        detail = client.get(f"/reviews/{fork['id']}/detail", headers=bob.headers).json()
        assert detail["forked_from_id"] is None and detail["forked_from"] is None
