"""Dish reviews: create/edit/delete, validation, ownership, likes, comments, recipes."""
import pytest

from helpers import homemade, meal, review


class TestCreate:
    def test_restaurant_review(self, client, alice):
        r = review(client, alice, dish_name="  Ramen  ", rating=4.5)
        assert r["dish_name"] == "Ramen"          # trimmed
        assert r["rating"] == 4.5
        assert r["user_email"] == alice.email
        mine = client.get("/reviews", headers=alice.headers).json()
        assert [x["id"] for x in mine] == [r["id"]]

    @pytest.mark.parametrize("rating", [0, 0.25, 5.5, 3.3, -1])
    def test_invalid_ratings(self, client, alice, rating):
        r = client.post("/reviews", headers=alice.headers,
                        json={"dish_name": "X", "type": "restaurant", "restaurant_name": "Y", "rating": rating})
        assert r.status_code == 400

    @pytest.mark.parametrize("rating", [0.5, 1, 2.5, 5])
    def test_valid_ratings(self, client, alice, rating):
        assert review(client, alice, rating=rating)["rating"] == rating

    def test_invalid_type(self, client, alice):
        r = client.post("/reviews", headers=alice.headers,
                        json={"dish_name": "X", "type": "takeaway", "rating": 3})
        assert r.status_code == 400

    def test_homemade_with_ingredients(self, client, alice):
        r = homemade(client, alice, ingredients=[
            {"name": "Flour", "quantity": 200, "unit": "g"},
            {"name": "Milk", "quantity": 0.5, "unit": "l"},
        ])
        assert [i["name"] for i in r["ingredients"]] == ["Flour", "Milk"]
        assert r["ingredients"][1]["quantity"] == 0.5

    @pytest.mark.parametrize("ingredients", [
        [],                                                               # none at all
        [{"name": "Flour", "quantity": 0, "unit": "g"}],                  # no amount
        [{"name": "Flour", "quantity": 1, "unit": "handful"}],            # unknown unit
        [{"name": "Flour", "quantity": 1, "unit": "g"},
         {"name": "flour", "quantity": 2, "unit": "g"}],                  # listed twice
    ])
    def test_bad_ingredients(self, client, alice, ingredients):
        r = client.post("/reviews", headers=alice.headers,
                        json={"dish_name": "Pancakes", "type": "homemade", "rating": 4, "ingredients": ingredients})
        assert r.status_code == 400

    def test_tag_recipe_author(self, client, alice, bob):
        r = homemade(client, alice, recipe_owner_email=bob.email)
        assert r["recipe_owner_email"] == bob.email

    def test_tagging_yourself_as_recipe_author_means_own_recipe(self, client, alice):
        assert homemade(client, alice, recipe_owner_email=alice.email)["recipe_owner_email"] is None

    def test_recipe_author_must_exist(self, client, alice):
        r = client.post("/reviews", headers=alice.headers,
                        json={"dish_name": "Pancakes", "type": "homemade", "rating": 4,
                              "recipe_owner_email": "ghost@test.com",
                              "ingredients": [{"name": "Flour", "quantity": 1, "unit": "g"}]})
        assert r.status_code == 404

    def test_only_homemade_can_tag_recipe_author(self, client, alice, bob):
        r = client.post("/reviews", headers=alice.headers,
                        json={"dish_name": "Ramen", "type": "restaurant", "restaurant_name": "Ichiran",
                              "rating": 4, "recipe_owner_email": bob.email})
        assert r.status_code == 400


class TestEditDelete:
    def test_owner_can_edit(self, client, alice):
        r = review(client, alice)
        upd = client.patch(f"/reviews/{r['id']}", headers=alice.headers,
                           json={"dish_name": "Tonkotsu", "type": "restaurant", "restaurant_name": "Ichiran",
                                 "rating": 3})
        assert upd.status_code == 200
        assert upd.json()["dish_name"] == "Tonkotsu" and upd.json()["rating"] == 3

    def test_others_cannot_edit_or_delete(self, client, alice, bob):
        r = review(client, alice)
        upd = client.patch(f"/reviews/{r['id']}", headers=bob.headers,
                           json={"dish_name": "Hacked", "type": "restaurant", "rating": 1})
        assert upd.status_code == 404
        assert client.delete(f"/reviews/{r['id']}", headers=bob.headers).status_code == 404
        assert client.get(f"/reviews/{r['id']}/detail", headers=alice.headers).json()["dish_name"] == "Ramen"

    def test_owner_can_delete(self, client, alice, db):
        r = review(client, alice)
        assert client.delete(f"/reviews/{r['id']}", headers=alice.headers).status_code == 204
        assert client.get(f"/reviews/{r['id']}/detail", headers=alice.headers).status_code == 404

    def test_deleting_a_review_removes_its_likes_and_comments(self, client, alice, bob, db):
        r = review(client, alice)
        client.post(f"/reviews/{r['id']}/like", headers=bob.headers)
        client.post(f"/reviews/{r['id']}/comments", json={"content": "yum"}, headers=bob.headers)
        client.delete(f"/reviews/{r['id']}", headers=alice.headers)
        db.execute("SELECT (SELECT count(*) FROM review_likes) + (SELECT count(*) FROM review_comments)")
        assert db.fetchone()[0] == 0

    def test_meal_dishes_cannot_be_edited_or_deleted_on_their_own(self, client, alice):
        m = meal(client, alice)
        dish_id = m["dishes"][0]["id"]
        assert client.delete(f"/reviews/{dish_id}", headers=alice.headers).status_code == 400
        upd = client.patch(f"/reviews/{dish_id}", headers=alice.headers,
                           json={"dish_name": "X", "type": "restaurant", "rating": 3})
        assert upd.status_code == 400

    def test_my_reviews_excludes_meal_dishes(self, client, alice):
        meal(client, alice)
        r = review(client, alice)
        assert [x["id"] for x in client.get("/reviews", headers=alice.headers).json()] == [r["id"]]


class TestLikes:
    def test_like_toggles(self, client, alice, bob):
        r = review(client, alice)
        assert client.post(f"/reviews/{r['id']}/like", headers=bob.headers).json() == {"liked": True, "like_count": 1}
        assert client.post(f"/reviews/{r['id']}/like", headers=alice.headers).json() == {"liked": True, "like_count": 2}
        assert client.post(f"/reviews/{r['id']}/like", headers=bob.headers).json() == {"liked": False, "like_count": 1}

    def test_likes_list_and_detail(self, client, alice, bob):
        r = review(client, alice)
        client.post(f"/reviews/{r['id']}/like", headers=bob.headers)
        likes = client.get(f"/reviews/{r['id']}/likes", headers=alice.headers).json()
        assert [l["user_email"] for l in likes] == [bob.email]
        assert client.get(f"/reviews/{r['id']}/detail", headers=bob.headers).json()["user_liked"] is True
        assert client.get(f"/reviews/{r['id']}/detail", headers=alice.headers).json()["user_liked"] is False

    def test_like_missing_review(self, client, alice):
        assert client.post("/reviews/999/like", headers=alice.headers).status_code == 404


class TestComments:
    def test_threaded_comments(self, client, alice, bob):
        r = review(client, alice)
        top = client.post(f"/reviews/{r['id']}/comments", json={"content": " nice "}, headers=bob.headers)
        assert top.status_code == 201 and top.json()["content"] == "nice"
        reply = client.post(f"/reviews/{r['id']}/comments",
                            json={"content": "thanks", "parent_id": top.json()["id"]}, headers=alice.headers)
        assert reply.json()["parent_id"] == top.json()["id"]
        comments = client.get(f"/reviews/{r['id']}/comments", headers=alice.headers).json()
        assert [c["content"] for c in comments] == ["nice", "thanks"]
        assert client.get(f"/reviews/{r['id']}/detail", headers=alice.headers).json()["comment_count"] == 2

    def test_empty_comment(self, client, alice):
        r = review(client, alice)
        assert client.post(f"/reviews/{r['id']}/comments", json={"content": "   "},
                           headers=alice.headers).status_code == 400

    def test_reply_parent_must_be_on_the_same_review(self, client, alice):
        r1, r2 = review(client, alice), review(client, alice, dish_name="Gyoza")
        c = client.post(f"/reviews/{r1['id']}/comments", json={"content": "hi"}, headers=alice.headers).json()
        r = client.post(f"/reviews/{r2['id']}/comments", json={"content": "x", "parent_id": c["id"]},
                        headers=alice.headers)
        assert r.status_code == 400

    def test_only_the_author_can_delete_a_comment(self, client, alice, bob):
        r = review(client, alice)
        c = client.post(f"/reviews/{r['id']}/comments", json={"content": "hi"}, headers=bob.headers).json()
        assert client.delete(f"/reviews/{r['id']}/comments/{c['id']}", headers=alice.headers).status_code == 404
        assert client.delete(f"/reviews/{r['id']}/comments/{c['id']}", headers=bob.headers).status_code == 204

    def test_deleting_a_comment_deletes_its_replies(self, client, alice, bob):
        r = review(client, alice)
        top = client.post(f"/reviews/{r['id']}/comments", json={"content": "a"}, headers=bob.headers).json()
        client.post(f"/reviews/{r['id']}/comments", json={"content": "b", "parent_id": top["id"]}, headers=alice.headers)
        client.delete(f"/reviews/{r['id']}/comments/{top['id']}", headers=bob.headers)
        assert client.get(f"/reviews/{r['id']}/comments", headers=alice.headers).json() == []

    def test_comment_likes(self, client, alice, bob):
        r = review(client, alice)
        c = client.post(f"/reviews/{r['id']}/comments", json={"content": "hi"}, headers=bob.headers).json()
        assert client.post(f"/comments/review/{c['id']}/like", headers=alice.headers).json() == {"liked": True, "like_count": 1}
        comments = client.get(f"/reviews/{r['id']}/comments", headers=alice.headers).json()
        assert comments[0]["like_count"] == 1 and comments[0]["user_liked"] is True
        assert client.post(f"/comments/review/{c['id']}/like", headers=alice.headers).json()["liked"] is False
        assert client.post(f"/comments/pizza/{c['id']}/like", headers=alice.headers).status_code == 400
        assert client.post("/comments/review/999/like", headers=alice.headers).status_code == 404
