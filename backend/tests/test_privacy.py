"""Private accounts: "Only followers you approve can see your posts."

A private user's reviews and meals are visible to the author, approved followers,
and people tagged in that post; nobody else, through any endpoint.
"""
import pytest

from helpers import follow, meal, review


@pytest.fixture
def priv(make_user):
    return make_user("priv", private=True)


@pytest.fixture
def follower(client, make_user, priv):
    """Someone whose follow request priv approved."""
    f = make_user("follower")
    req = follow(client, f, priv)
    r = client.patch(f"/friends/requests/{req['id']}", json={"action": "accept"}, headers=priv.headers)
    assert r.status_code == 200
    return f


def visible_review_ids(client, viewer, author):
    return [r["id"] for r in client.get(f"/users/{author.email}/reviews", headers=viewer.headers).json()]


class TestWhoCanSee:
    def test_stranger_sees_nothing(self, client, alice, priv):
        r = review(client, priv)
        m = meal(client, priv)
        assert client.get(f"/users/{priv.email}/reviews", headers=alice.headers).json() == []
        assert client.get(f"/users/{priv.email}/meals", headers=alice.headers).json() == []
        assert client.get(f"/reviews/{r['id']}/detail", headers=alice.headers).status_code == 404
        assert client.get(f"/meals/{m['id']}", headers=alice.headers).status_code == 404
        assert client.get(f"/meals/{m['id']}/detail", headers=alice.headers).status_code == 404
        assert client.get("/reviews/all", headers=alice.headers).json() == []

    def test_follower_and_author_see_everything(self, client, priv, follower):
        r = review(client, priv)
        m = meal(client, priv)
        for viewer in (priv, follower):
            assert visible_review_ids(client, viewer, priv) == [r["id"]]
            assert [x["id"] for x in client.get(f"/users/{priv.email}/meals", headers=viewer.headers).json()] == [m["id"]]
            assert client.get(f"/reviews/{r['id']}/detail", headers=viewer.headers).status_code == 200
            assert client.get(f"/meals/{m['id']}/detail", headers=viewer.headers).status_code == 200

    def test_pending_request_is_not_enough(self, client, alice, priv):
        follow(client, alice, priv)                     # pending
        review(client, priv)
        assert visible_review_ids(client, alice, priv) == []

    def test_approving_then_unfollowing(self, client, alice, priv):
        r = review(client, priv)
        req = follow(client, alice, priv)
        client.patch(f"/friends/requests/{req['id']}", json={"action": "accept"}, headers=priv.headers)
        assert visible_review_ids(client, alice, priv) == [r["id"]]
        client.delete(f"/follow/{priv.email}", headers=alice.headers)
        assert visible_review_ids(client, alice, priv) == []

    def test_switching_to_public_shows_posts_again(self, client, alice, priv):
        r = review(client, priv)
        client.patch("/me/privacy", json={"is_private": False}, headers=priv.headers)
        assert visible_review_ids(client, alice, priv) == [r["id"]]

    def test_tagged_people_see_that_post_only(self, client, alice, priv):
        follow(client, priv, alice)                     # priv follows alice, so priv can tag her
        tagged = review(client, priv, tagged_emails=[alice.email])
        other = review(client, priv, dish_name="Gyoza")
        assert client.get(f"/reviews/{tagged['id']}/detail", headers=alice.headers).status_code == 200
        assert client.get(f"/reviews/{other['id']}/detail", headers=alice.headers).status_code == 404

    def test_public_accounts_are_unaffected(self, client, alice, bob):
        r = review(client, bob)
        assert visible_review_ids(client, alice, bob) == [r["id"]]


class TestNoBackDoors:
    def test_likes_and_comments_are_hidden_and_locked(self, client, alice, priv):
        r = review(client, priv)
        m = meal(client, priv)
        for base in (f"/reviews/{r['id']}", f"/meals/{m['id']}"):
            assert client.get(f"{base}/likes", headers=alice.headers).status_code == 404
            assert client.get(f"{base}/comments", headers=alice.headers).status_code == 404
            assert client.post(f"{base}/like", headers=alice.headers).status_code == 404
            assert client.post(f"{base}/comments", json={"content": "hi"}, headers=alice.headers).status_code == 404

    def test_comment_likes(self, client, alice, priv):
        r = review(client, priv)
        c = client.post(f"/reviews/{r['id']}/comments", json={"content": "mine"}, headers=priv.headers).json()
        assert client.post(f"/comments/review/{c['id']}/like", headers=alice.headers).status_code == 404

    def test_place_pages_leave_out_hidden_reviews(self, client, alice, bob, priv):
        review(client, priv, rating=1, dish_name="Ramen", restaurant_name="Ichiran")
        review(client, bob, rating=5, dish_name="Ramen", restaurant_name="Ichiran")
        page = client.get("/restaurants/Ichiran/page", headers=alice.headers).json()
        assert page["total_reviews"] == 1 and page["avg_rating"] == 5.0
        assert {x["user_email"] for x in page["reviews"]} == {bob.email}
        dish = client.get("/dishes/Ramen/restaurant/Ichiran", headers=alice.headers).json()
        assert dish["review_count"] == 1
        # ...but the author still sees their own review counted
        assert client.get("/restaurants/Ichiran/page", headers=priv.headers).json()["total_reviews"] == 2

    def test_place_only_reviewed_privately_does_not_exist_for_strangers(self, client, alice, priv):
        review(client, priv, dish_name="Secret", restaurant_name="Hidden Place")
        assert client.get("/restaurants", headers=alice.headers).json() == []
        assert client.get("/restaurants/Hidden Place/page", headers=alice.headers).status_code == 404
        assert client.get("/search/dishes-restaurants", params={"q": "secret"}, headers=alice.headers).json() == []

    def test_reposts_do_not_leak_private_posts(self, client, alice, bob, priv):
        # priv tags bob (who may see it and repost it); alice follows bob but not priv
        follow(client, priv, bob)
        r = review(client, priv, tagged_emails=[bob.email])
        assert client.post(f"/posts/review/{r['id']}/repost", headers=bob.headers).json() == {"reposted": True}
        follow(client, alice, bob)
        assert visible_review_ids(client, alice, bob) == []
        assert all(i["id"] != r["id"] for i in client.get("/feed", headers=alice.headers).json())
        assert visible_review_ids(client, bob, bob) == [r["id"]]   # bob still sees his own repost

    def test_list_ratings_ignore_hidden_reviews(self, client, alice, priv):
        review(client, priv, rating=1)
        lst = client.post("/lists", json={"name": "L"}, headers=alice.headers).json()
        client.post(f"/lists/{lst['id']}/items", json={"item_type": "dish", "name": "Ramen", "restaurant_name": "Ichiran"},
                    headers=alice.headers)
        item = client.get(f"/lists/{lst['id']}/items", headers=alice.headers).json()[0]
        assert item["review_count"] == 0 and item["avg_rating"] is None
