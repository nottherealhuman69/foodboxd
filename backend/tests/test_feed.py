"""The home feed: whose posts show up, and how reposts appear."""
from helpers import follow, meal, review


def feed(client, user):
    r = client.get("/feed", headers=user.headers)
    assert r.status_code == 200, r.text
    return r.json()


def keys(items):
    return {(i["kind"], i["id"]) for i in items}


def test_empty_when_following_nobody(client, alice, bob):
    review(client, bob)
    assert feed(client, alice) == []


def test_shows_only_people_i_follow(client, alice, bob, carol):
    follow(client, alice, bob)
    b_review, b_meal = review(client, bob), meal(client, bob)
    review(client, carol)       # not followed
    review(client, alice)       # my own posts aren't in my feed
    assert keys(feed(client, alice)) == {("review", b_review["id"]), ("meal", b_meal["id"])}


def test_meal_dishes_are_not_separate_feed_items(client, alice, bob):
    follow(client, alice, bob)
    m = meal(client, bob)
    items = feed(client, alice)
    assert keys(items) == {("meal", m["id"])}
    assert items[0]["dish_count"] == 2


def test_pending_follow_shows_nothing(client, alice, make_user):
    priv = make_user("priv", private=True)
    follow(client, alice, priv)          # pending
    review(client, priv)
    meal(client, priv)
    assert feed(client, alice) == []


def test_newest_first_and_like_state(client, alice, bob):
    follow(client, alice, bob)
    first = review(client, bob, dish_name="First")
    meal(client, bob)
    last = review(client, bob, dish_name="Last")
    client.post(f"/reviews/{first['id']}/like", headers=alice.headers)
    items = feed(client, alice)
    assert items[0]["id"] == last["id"]
    by_id = {(i["kind"], i["id"]): i for i in items}
    assert by_id[("review", first["id"])]["user_liked"] is True
    assert by_id[("review", first["id"])]["like_count"] == 1


def test_unfollow_removes_their_posts(client, alice, bob):
    follow(client, alice, bob)
    review(client, bob)
    meal(client, bob)
    client.delete(f"/follow/{bob.email}", headers=alice.headers)
    assert feed(client, alice) == []


def test_repost_by_someone_i_follow_shows_with_their_name(client, alice, bob, carol):
    # carol tags bob (she must follow him to tag him), bob reposts it, alice follows only bob
    follow(client, carol, bob)
    r = review(client, carol, tagged_emails=[bob.email])
    assert client.post(f"/posts/review/{r['id']}/repost", headers=bob.headers).json() == {"reposted": True}
    follow(client, alice, bob)
    meal(client, bob)
    item = next(i for i in feed(client, alice) if i["id"] == r["id"] and i["kind"] == "review")
    assert item["user_email"] == carol.email
    assert item["reposted_by"]["email"] == bob.email


def test_works_when_followed_users_have_no_meals(client, alice, bob):
    # regression: `reposts` used to be set only inside the meals loop (500 with no meals)
    follow(client, alice, bob)
    r = review(client, bob)
    assert [i["id"] for i in feed(client, alice)] == [r["id"]]
