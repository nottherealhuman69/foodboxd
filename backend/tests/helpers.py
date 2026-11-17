"""Small helpers shared by the test files: `from helpers import follow, review, ...`"""


def follow(client, follower, followee):
    """follower follows followee (accepted immediately if followee is public)."""
    r = client.post("/friends/request", json={"addressee_email": followee.email}, headers=follower.headers)
    assert r.status_code == 201, r.text
    return r.json()


def mutual(client, a, b):
    """a and b follow each other (both public)."""
    follow(client, a, b)
    follow(client, b, a)


def review(client, user, **overrides):
    """Create a restaurant review (override any field) and return the response JSON."""
    body = {"dish_name": "Ramen", "type": "restaurant", "restaurant_name": "Ichiran",
            "rating": 4.5, "review": "great broth"}
    body.update(overrides)
    r = client.post("/reviews", json=body, headers=user.headers)
    assert r.status_code == 201, r.text
    return r.json()


def homemade(client, user, **overrides):
    """Create a homemade review with one ingredient."""
    body = {"dish_name": "Pancakes", "type": "homemade", "rating": 4, "recipe": "Mix and fry",
            "ingredients": [{"name": "Flour", "quantity": 200, "unit": "g"}]}
    body.update(overrides)
    return review(client, user, **body)


def meal(client, user, **overrides):
    """Create a meal with two dishes and return the response JSON."""
    body = {"restaurant_name": "Dishoom", "title": "Dinner", "rating": 4,
            "dishes": [{"dish_name": "Black Daal", "rating": 5},
                       {"dish_name": "Naan", "rating": 4}]}
    body.update(overrides)
    r = client.post("/meals", json=body, headers=user.headers)
    assert r.status_code == 201, r.text
    return r.json()
