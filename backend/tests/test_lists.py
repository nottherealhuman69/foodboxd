"""Personal lists, the try-list and group lists."""
import pytest

from helpers import follow, mutual, review


def item(item_type="dish", name="Ramen", restaurant_name="Ichiran", **extra):
    return {"item_type": item_type, "name": name, "restaurant_name": restaurant_name, **extra}


# ── Personal lists ───────────────────────────────────────────────────────────
class TestPersonalLists:
    def make(self, client, user, name="Favourites", is_public=True):
        r = client.post("/lists", json={"name": name, "is_public": is_public}, headers=user.headers)
        assert r.status_code == 201, r.text
        return r.json()

    def test_create_add_and_read(self, client, alice):
        lst = self.make(client, alice)
        assert client.post(f"/lists/{lst['id']}/items", json=item(), headers=alice.headers).status_code == 201
        lists = client.get("/lists", headers=alice.headers).json()
        assert [(l["name"], l["item_count"]) for l in lists] == [("Favourites", 1)]
        assert [i["name"] for i in client.get(f"/lists/{lst['id']}/items", headers=alice.headers).json()] == ["Ramen"]

    def test_empty_name(self, client, alice):
        assert client.post("/lists", json={"name": "  "}, headers=alice.headers).status_code == 400

    def test_duplicate_item_is_case_insensitive(self, client, alice):
        lst = self.make(client, alice)
        client.post(f"/lists/{lst['id']}/items", json=item(), headers=alice.headers)
        r = client.post(f"/lists/{lst['id']}/items", json=item(name="RAMEN", restaurant_name="ichiran"),
                        headers=alice.headers)
        assert r.status_code == 409

    def test_invalid_item(self, client, alice):
        lst = self.make(client, alice)
        assert client.post(f"/lists/{lst['id']}/items", json=item(item_type="drink"), headers=alice.headers).status_code == 400
        assert client.post(f"/lists/{lst['id']}/items", json=item(name=" "), headers=alice.headers).status_code == 400

    def test_recipe_item_owner_defaults_to_me(self, client, alice):
        lst = self.make(client, alice)
        r = client.post(f"/lists/{lst['id']}/items", json=item("recipe", "Pancakes", None), headers=alice.headers)
        assert r.json()["recipe_owner_email"] == alice.email

    def test_item_shows_community_rating(self, client, alice, bob):
        review(client, bob, rating=4)
        review(client, alice, rating=5)
        lst = self.make(client, alice)
        client.post(f"/lists/{lst['id']}/items", json=item(), headers=alice.headers)
        got = client.get(f"/lists/{lst['id']}/items", headers=alice.headers).json()[0]
        assert got["avg_rating"] == 4.5 and got["review_count"] == 2 and got["my_rating"] == 5

    def test_only_the_owner_can_change_a_list(self, client, alice, bob):
        lst = self.make(client, alice)
        it = client.post(f"/lists/{lst['id']}/items", json=item(), headers=alice.headers).json()
        assert client.post(f"/lists/{lst['id']}/items", json=item(name="Gyoza"), headers=bob.headers).status_code == 404
        assert client.delete(f"/lists/{lst['id']}/items/{it['id']}", headers=bob.headers).status_code == 404
        assert client.delete(f"/lists/{lst['id']}", headers=bob.headers).status_code == 404

    def test_private_lists_are_hidden_from_others(self, client, alice, bob):
        public = self.make(client, alice, "Public")
        private = self.make(client, alice, "Secret", is_public=False)
        assert client.get(f"/lists/{public['id']}/items", headers=bob.headers).status_code == 200
        assert client.get(f"/lists/{private['id']}/items", headers=bob.headers).status_code == 404
        names = [l["name"] for l in client.get(f"/users/{alice.email}/lists", headers=bob.headers).json()]
        assert names == ["Public"]

    def test_deleting_a_list_deletes_its_items(self, client, alice, db):
        lst = self.make(client, alice)
        client.post(f"/lists/{lst['id']}/items", json=item(), headers=alice.headers)
        assert client.delete(f"/lists/{lst['id']}", headers=alice.headers).status_code == 204
        db.execute("SELECT count(*) FROM list_items")
        assert db.fetchone()[0] == 0


# ── Try-list ─────────────────────────────────────────────────────────────────
class TestTrylist:
    def test_add_check_and_remove(self, client, alice):
        r = client.post("/trylist", json={"item_type": "dish", "dish_name": "Ramen", "restaurant_name": "Ichiran"},
                        headers=alice.headers)
        assert r.status_code == 201
        check = client.get("/trylist/check", params={"item_type": "dish", "restaurant_name": "ichiran",
                                                     "dish_name": "Ramen"}, headers=alice.headers).json()
        assert check == {"in_trylist": True, "id": r.json()["id"]}
        assert client.delete(f"/trylist/{r.json()['id']}", headers=alice.headers).status_code == 204
        assert client.get("/trylist", headers=alice.headers).json() == []

    def test_restaurant_item(self, client, alice):
        r = client.post("/trylist", json={"item_type": "restaurant", "restaurant_name": "Dishoom"}, headers=alice.headers)
        assert r.status_code == 201 and r.json()["dish_name"] is None

    @pytest.mark.parametrize("body", [
        {"item_type": "drink", "restaurant_name": "X"},
        {"item_type": "dish", "restaurant_name": "X"},            # dish needs dish_name
        {"item_type": "dish", "dish_name": "Y"},                  # ...and a restaurant
        {"item_type": "restaurant"},
    ])
    def test_validation(self, client, alice, body):
        assert client.post("/trylist", json=body, headers=alice.headers).status_code == 400

    def test_duplicate(self, client, alice):
        body = {"item_type": "restaurant", "restaurant_name": "Dishoom"}
        client.post("/trylist", json=body, headers=alice.headers)
        r = client.post("/trylist", json={**body, "restaurant_name": "DISHOOM"}, headers=alice.headers)
        assert r.status_code == 409

    def test_cannot_remove_someone_elses(self, client, alice, bob):
        r = client.post("/trylist", json={"item_type": "restaurant", "restaurant_name": "Dishoom"}, headers=alice.headers)
        assert client.delete(f"/trylist/{r.json()['id']}", headers=bob.headers).status_code == 404

    def test_check_route_is_not_mistaken_for_an_id(self, client, alice):
        r = client.get("/trylist/check", params={"item_type": "restaurant", "restaurant_name": "X"},
                       headers=alice.headers)
        assert r.status_code == 200 and r.json()["in_trylist"] is False


# ── Group lists ──────────────────────────────────────────────────────────────
@pytest.fixture
def group(client, alice, bob):
    """alice owns 'Trip'; bob (her friend) was invited and accepted."""
    mutual(client, alice, bob)
    gl = client.post("/group-lists", json={"name": "Trip", "invite_emails": [bob.email]}, headers=alice.headers).json()
    r = client.patch(f"/group-lists/{gl['id']}/invite", json={"action": "accept"}, headers=bob.headers)
    assert r.status_code == 200
    return gl


class TestGroupLists:
    def test_create_invites_only_friends(self, client, alice, bob, carol):
        follow(client, alice, bob)
        gl = client.post("/group-lists", json={"name": "Trip", "invite_emails": [bob.email, carol.email]},
                         headers=alice.headers).json()
        assert gl["my_role"] == "owner" and gl["pending_count"] == 1
        assert gl["skipped"] == [carol.email]
        invites = client.get("/group-lists/invites", headers=bob.headers).json()
        assert [i["group_list_id"] for i in invites] == [gl["id"]]
        assert client.get("/group-lists/invites", headers=carol.headers).json() == []

    def test_accepting_an_invite_joins_the_list(self, client, alice, bob, group):
        assert [g["id"] for g in client.get("/group-lists", headers=bob.headers).json()] == [group["id"]]
        members = client.get(f"/group-lists/{group['id']}", headers=bob.headers).json()["members"]
        assert {(m["email"], m["role"], m["status"]) for m in members} == {
            (alice.email, "owner", "accepted"), (bob.email, "member", "accepted")}

    def test_declined_invite(self, client, alice, bob):
        mutual(client, alice, bob)
        gl = client.post("/group-lists", json={"name": "Trip", "invite_emails": [bob.email]}, headers=alice.headers).json()
        client.patch(f"/group-lists/{gl['id']}/invite", json={"action": "decline"}, headers=bob.headers)
        assert client.get("/group-lists", headers=bob.headers).json() == []
        assert client.get(f"/group-lists/{gl['id']}", headers=bob.headers).status_code == 404

    def test_private_list_hidden_public_list_readable(self, client, alice, carol, group):
        assert client.get(f"/group-lists/{group['id']}", headers=carol.headers).status_code == 404
        assert client.get(f"/group-lists/{group['id']}/items", headers=carol.headers).status_code == 404
        client.patch(f"/group-lists/{group['id']}/visibility", json={"is_public": True}, headers=alice.headers)
        assert client.get(f"/group-lists/{group['id']}", headers=carol.headers).json()["my_role"] is None
        assert client.get(f"/group-lists/{group['id']}/items", headers=carol.headers).status_code == 200
        # outsiders still can't change anything
        assert client.post(f"/group-lists/{group['id']}/items", json=item(), headers=carol.headers).status_code == 404

    def test_public_group_lists_on_profile(self, client, alice, bob, carol, group):
        assert client.get(f"/users/{bob.email}/group-lists", headers=carol.headers).json() == []
        client.patch(f"/group-lists/{group['id']}/visibility", json={"is_public": True}, headers=bob.headers)
        assert [g["id"] for g in client.get(f"/users/{bob.email}/group-lists", headers=carol.headers).json()] == [group["id"]]

    def test_pending_member_cannot_add_items(self, client, alice, bob):
        mutual(client, alice, bob)
        gl = client.post("/group-lists", json={"name": "Trip", "invite_emails": [bob.email]}, headers=alice.headers).json()
        assert client.post(f"/group-lists/{gl['id']}/items", json=item(), headers=bob.headers).status_code == 404

    def test_items_duplicates_and_who_can_remove(self, client, alice, bob, carol, group):
        gid = group["id"]
        # bob (a member) invites his own friend carol
        mutual(client, bob, carol)
        assert client.post(f"/group-lists/{gid}/invite", json={"emails": [carol.email]},
                           headers=bob.headers).json()["invited"] == [carol.email]
        client.patch(f"/group-lists/{gid}/invite", json={"action": "accept"}, headers=carol.headers)

        bobs = client.post(f"/group-lists/{gid}/items", json=item(), headers=bob.headers)
        assert bobs.status_code == 201
        dupe = client.post(f"/group-lists/{gid}/items", json=item(name="ramen"), headers=carol.headers)
        assert dupe.status_code == 409 and "@bob" in dupe.json()["detail"]
        carols = client.post(f"/group-lists/{gid}/items", json=item(name="Gyoza"), headers=carol.headers).json()

        assert client.delete(f"/group-lists/{gid}/items/{bobs.json()['id']}", headers=carol.headers).status_code == 403
        assert client.delete(f"/group-lists/{gid}/items/{carols['id']}", headers=carol.headers).status_code == 204
        assert client.delete(f"/group-lists/{gid}/items/{bobs.json()['id']}", headers=alice.headers).status_code == 204

    def test_leaving(self, client, alice, bob, group):
        assert client.post(f"/group-lists/{group['id']}/leave", headers=alice.headers).status_code == 400  # owner
        assert client.post(f"/group-lists/{group['id']}/leave", headers=bob.headers).status_code == 204
        assert client.get(f"/group-lists/{group['id']}", headers=bob.headers).status_code == 404

    def test_only_owner_can_delete(self, client, alice, bob, group, db):
        client.post(f"/group-lists/{group['id']}/items", json=item(), headers=bob.headers)
        assert client.delete(f"/group-lists/{group['id']}", headers=bob.headers).status_code == 404
        assert client.delete(f"/group-lists/{group['id']}", headers=alice.headers).status_code == 204
        db.execute("SELECT (SELECT count(*) FROM group_list_items) + (SELECT count(*) FROM group_list_members)")
        assert db.fetchone()[0] == 0

    def test_invite_shows_in_unseen_count(self, client, alice, bob):
        mutual(client, alice, bob)
        before = client.get("/notifications/unseen_count", headers=bob.headers).json()["count"]
        client.post("/group-lists", json={"name": "Trip", "invite_emails": [bob.email]}, headers=alice.headers)
        assert client.get("/notifications/unseen_count", headers=bob.headers).json()["count"] == before + 1
