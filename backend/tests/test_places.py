"""Restaurant, dish and recipe pages, search, and notifications."""
from datetime import datetime, timedelta

from helpers import follow, homemade, meal, review


class TestPlaces:
    def test_restaurant_page_includes_meal_dishes(self, client, alice, bob):
        review(client, alice, dish_name="Ramen", restaurant_name="Ichiran", rating=5)
        review(client, bob, dish_name="Ramen", restaurant_name="Ichiran", rating=4)
        meal(client, bob, restaurant_name="Ichiran", dishes=[{"dish_name": "Gyoza", "rating": 3}])
        homemade(client, alice, dish_name="Ramen")                       # homemade: not a restaurant review

        page = client.get("/restaurants/ICHIRAN/page", headers=alice.headers).json()
        assert page["total_reviews"] == 3 and page["total_dishes"] == 2
        assert page["avg_rating"] == 4.0
        assert page["created_by_email"] == alice.email
        assert {d["dish_name"]: d["avg_rating"] for d in page["dishes"]} == {"Ramen": 4.5, "Gyoza": 3.0}

    def test_restaurant_lists_and_404(self, client, alice):
        review(client, alice, restaurant_name="Ichiran", dish_name="Ramen")
        homemade(client, alice)
        assert client.get("/restaurants", headers=alice.headers).json() == ["Ichiran"]
        assert client.get("/restaurants/Ichiran/dishes", headers=alice.headers).json() == ["Ramen"]
        assert client.get("/restaurants/Nowhere/page", headers=alice.headers).status_code == 404

    def test_dish_page(self, client, alice, bob):
        review(client, alice, rating=5)
        review(client, bob, rating=3)
        page = client.get("/dishes/ramen/restaurant/Ichiran", headers=alice.headers).json()
        assert page["review_count"] == 2 and page["avg_rating"] == 4.0
        assert {r["user_email"] for r in page["reviews"]} == {alice.email, bob.email}
        assert client.get("/dishes/Pho/restaurant/Ichiran", headers=alice.headers).status_code == 404
        assert client.get("/dishes", headers=alice.headers).json()[0]["review_count"] == 2

    def test_names_with_spaces_and_symbols(self, client, alice):
        review(client, alice, dish_name="Fish & Chips", restaurant_name="Bob's Café")
        r = client.get("/dishes/Fish%20%26%20Chips/restaurant/Bob's%20Caf%C3%A9", headers=alice.headers)
        assert r.status_code == 200 and r.json()["dish_name"] == "Fish & Chips"

    def test_search(self, client, alice):
        review(client, alice, dish_name="Ramen", restaurant_name="Ichiran")
        review(client, alice, dish_name="Gyoza", restaurant_name="Ippudo")
        dishes = client.get("/search/dishes-restaurants", params={"q": "ram"}, headers=alice.headers).json()
        assert dishes == [{"name": "Ramen", "restaurant_name": "Ichiran"}]
        places = client.get("/search/dishes-restaurants", params={"q": "i", "item_type": "restaurant"},
                            headers=alice.headers).json()
        assert [p["name"] for p in places] == ["Ichiran", "Ippudo"]
        assert client.get("/search/dishes-restaurants", params={"q": " "}, headers=alice.headers).json() == []

    def test_recipe_page_groups_by_recipe_author(self, client, alice, bob):
        homemade(client, alice, dish_name="Pancakes", rating=5, recipe="Alice's way")
        homemade(client, bob, dish_name="pancakes", rating=3, recipe_owner_email=alice.email, recipe="")
        homemade(client, bob, dish_name="Pancakes", rating=1, recipe="Bob's own")
        page = client.get("/recipes/page", params={"dish_name": "Pancakes", "owner": alice.email},
                          headers=bob.headers).json()
        assert page["review_count"] == 2 and page["avg_rating"] == 4.0
        assert page["recipe"] == "Alice's way"
        assert page["ingredients"] == [{"name": "Flour", "quantity": 200.0, "unit": "g"}]
        assert client.get("/recipes/page", params={"dish_name": "Waffles", "owner": alice.email},
                          headers=bob.headers).status_code == 404


class TestNotifications:
    def test_activity_from_others_only(self, client, alice, bob):
        follow(client, bob, alice)
        r = review(client, alice)
        client.post(f"/reviews/{r['id']}/like", headers=alice.headers)            # own like: no notification
        client.post(f"/reviews/{r['id']}/like", headers=bob.headers)
        client.post(f"/reviews/{r['id']}/comments", json={"content": "hi"}, headers=bob.headers)
        review(client, bob, tagged_emails=[alice.email])                          # bob tags alice

        events = client.get("/notifications/activity", headers=alice.headers).json()
        assert sorted(e["type"] for e in events) == ["comment", "like", "tag"]
        assert {e["actor_email"] for e in events} == {bob.email}
        tag = next(e for e in events if e["type"] == "tag")
        assert tag["user_reposted"] is False

    def test_meal_activity(self, client, alice, bob):
        m = meal(client, alice)
        client.post(f"/meals/{m['id']}/like", headers=bob.headers)
        client.post(f"/meals/{m['id']}/comments", json={"content": "hi"}, headers=bob.headers)
        events = client.get("/notifications/activity", headers=alice.headers).json()
        assert sorted((e["type"], e["target_type"]) for e in events) == [("comment", "meal"), ("like", "meal")]

    def test_unseen_count(self, client, alice, bob, make_user):
        priv = make_user("priv", private=True)
        req = follow(client, bob, priv)                   # bob is an approved follower...
        client.patch(f"/friends/requests/{req['id']}", json={"action": "accept"}, headers=priv.headers)
        follow(client, alice, priv)                       # ...alice's request is still pending (counts)
        r = review(client, priv)
        client.post(f"/reviews/{r['id']}/like", headers=bob.headers)   # bob's like counts
        assert client.get("/notifications/unseen_count", headers=priv.headers).json() == {"count": 2}

        later = (datetime.now() + timedelta(days=1)).isoformat()
        r = client.get("/notifications/unseen_count", params={"since": later}, headers=priv.headers)
        assert r.json() == {"count": 1}                   # the like is older than `since`; the request isn't time-based


class TestSpellings:
    def test_spellings_of_one_restaurant_are_merged(self, client, alice, bob, carol):
        review(client, alice, restaurant_name="Ichiran", dish_name="Ramen", rating=5)
        review(client, bob, restaurant_name="Ichiran", dish_name="ramen", rating=4)
        review(client, carol, restaurant_name="ichiran", dish_name="Gyoza", rating=3)
        page = client.get("/restaurants/ICHIRAN/page", headers=alice.headers).json()
        assert page["restaurant_name"] == "Ichiran"            # the most common spelling
        assert page["total_reviews"] == 3 and page["avg_rating"] == 4.0
        assert page["total_dishes"] == 2
        # Ramen/ramen is a 1-1 tie, so either spelling may be shown
        assert {d["dish_name"].lower(): d["review_count"] for d in page["dishes"]} == {"ramen": 2, "gyoza": 1}
        assert client.get("/restaurants", headers=alice.headers).json() == ["Ichiran"]
        assert client.get("/dishes/RAMEN/restaurant/ichiran", headers=alice.headers).json()["review_count"] == 2

    def test_percent_sign_is_not_a_wildcard(self, client, alice):
        review(client, alice, restaurant_name="100% Vegan", dish_name="Bowl")
        review(client, alice, restaurant_name="100 Burgers", dish_name="Burger")
        page = client.get("/restaurants/100%25%20Vegan/page", headers=alice.headers).json()
        assert page["total_reviews"] == 1
