"""Meals (multi-dish posts): create/edit/delete, validation, ownership, likes, comments."""
import pytest

from helpers import meal


def dishes(*pairs):
    return [{"dish_name": n, "rating": r} for n, r in pairs]


class TestCreate:
    def test_create_and_read(self, client, alice):
        m = meal(client, alice, dishes=dishes(("Daal", 5), ("Naan", 4)), rating=4.5)
        assert m["kind"] == "meal" and m["rating"] == 4.5
        assert [d["dish_name"] for d in m["dishes"]] == ["Daal", "Naan"]
        assert m["dish_count"] == 2 and m["dish_avg"] == 4.5

        got = client.get(f"/meals/{m['id']}", headers=alice.headers).json()
        assert got["dishes"] == m["dishes"]
        assert [x["id"] for x in client.get("/meals", headers=alice.headers).json()] == [m["id"]]

    def test_blank_dish_rows_are_ignored(self, client, alice):
        m = meal(client, alice, dishes=dishes(("Daal", 5), ("   ", 3)))
        assert m["dish_count"] == 1

    @pytest.mark.parametrize("body, why", [
        ({"restaurant_name": "  ", "rating": 4, "dishes": dishes(("Daal", 5))}, "no restaurant"),
        ({"restaurant_name": "Dishoom", "rating": 4, "dishes": []}, "no dishes"),
        ({"restaurant_name": "Dishoom", "rating": 4, "dishes": dishes(("Daal", 5), ("daal", 4))}, "dish twice"),
        ({"restaurant_name": "Dishoom", "rating": 4, "dishes": dishes(("Daal", 7))}, "bad dish rating"),
        ({"restaurant_name": "Dishoom", "rating": 0, "dishes": dishes(("Daal", 5))}, "bad overall rating"),
    ])
    def test_validation(self, client, alice, body, why):
        assert client.post("/meals", json=body, headers=alice.headers).status_code == 400, why

    def test_failed_meal_saves_nothing(self, client, alice, db):
        client.post("/meals", headers=alice.headers,
                    json={"restaurant_name": "Dishoom", "rating": 4, "dishes": dishes(("Daal", 5), ("daal", 4))})
        db.execute("SELECT (SELECT count(*) FROM meals) + (SELECT count(*) FROM dish_reviews)")
        assert db.fetchone()[0] == 0


class TestEditDelete:
    def test_edit_keeps_renames_adds_and_removes_dishes(self, client, alice):
        m = meal(client, alice, dishes=dishes(("Daal", 5), ("Naan", 4)))
        daal, naan = m["dishes"]
        r = client.patch(f"/meals/{m['id']}", headers=alice.headers, json={
            "restaurant_name": "Dishoom Shoreditch", "title": "Lunch", "rating": 3.5,
            "dishes": [{"id": daal["id"], "dish_name": "House Daal", "rating": 4.5},
                       {"dish_name": "Chai", "rating": 3}],
        })
        assert r.status_code == 200
        out = r.json()
        assert out["title"] == "Lunch" and out["restaurant_name"] == "Dishoom Shoreditch"
        by_name = {d["dish_name"]: d for d in out["dishes"]}
        assert set(by_name) == {"House Daal", "Chai"}
        assert by_name["House Daal"]["id"] == daal["id"]            # same row, renamed
        assert naan["id"] not in {d["id"] for d in out["dishes"]}   # removed

    def test_others_cannot_edit_or_delete(self, client, alice, bob):
        m = meal(client, alice)
        r = client.patch(f"/meals/{m['id']}", headers=bob.headers,
                         json={"restaurant_name": "X", "rating": 3, "dishes": dishes(("Y", 3))})
        assert r.status_code == 404
        assert client.delete(f"/meals/{m['id']}", headers=bob.headers).status_code == 404

    def test_delete_removes_its_dishes(self, client, alice, db):
        m = meal(client, alice)
        assert client.delete(f"/meals/{m['id']}", headers=alice.headers).status_code == 204
        assert client.get(f"/meals/{m['id']}", headers=alice.headers).status_code == 404
        db.execute("SELECT count(*) FROM dish_reviews")
        assert db.fetchone()[0] == 0


class TestLikesAndComments:
    def test_likes(self, client, alice, bob):
        m = meal(client, alice)
        assert client.post(f"/meals/{m['id']}/like", headers=bob.headers).json() == {"liked": True, "like_count": 1}
        assert [l["user_email"] for l in client.get(f"/meals/{m['id']}/likes", headers=alice.headers).json()] == [bob.email]
        assert client.get(f"/meals/{m['id']}/detail", headers=bob.headers).json()["user_liked"] is True
        assert client.post(f"/meals/{m['id']}/like", headers=bob.headers).json() == {"liked": False, "like_count": 0}
        assert client.post("/meals/999/like", headers=bob.headers).status_code == 404

    def test_comments(self, client, alice, bob):
        m = meal(client, alice)
        c = client.post(f"/meals/{m['id']}/comments", json={"content": "jealous"}, headers=bob.headers)
        assert c.status_code == 201
        reply = client.post(f"/meals/{m['id']}/comments", json={"content": "ha", "parent_id": c.json()["id"]},
                            headers=alice.headers)
        assert reply.status_code == 201
        assert [x["content"] for x in client.get(f"/meals/{m['id']}/comments", headers=alice.headers).json()] == ["jealous", "ha"]
        assert client.get(f"/meals/{m['id']}/detail", headers=alice.headers).json()["comment_count"] == 2
        assert client.post(f"/meals/{m['id']}/comments", json={"content": " "}, headers=bob.headers).status_code == 400
        assert client.delete(f"/meals/{m['id']}/comments/{c.json()['id']}", headers=alice.headers).status_code == 404
        assert client.delete(f"/meals/{m['id']}/comments/{c.json()['id']}", headers=bob.headers).status_code == 204

    def test_comment_likes(self, client, alice, bob):
        m = meal(client, alice)
        c = client.post(f"/meals/{m['id']}/comments", json={"content": "hi"}, headers=bob.headers).json()
        assert client.post(f"/comments/meal/{c['id']}/like", headers=alice.headers).json() == {"liked": True, "like_count": 1}

    def test_someone_elses_meals(self, client, alice, bob):
        m = meal(client, bob)
        assert [x["id"] for x in client.get(f"/users/{bob.email}/meals", headers=alice.headers).json()] == [m["id"]]
