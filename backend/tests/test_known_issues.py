"""Bugs and gaps the tests found in the current code but that aren't fixed yet.

Each test describes how the app SHOULD behave and is marked xfail ("expected to
fail") because the code doesn't do that yet. The suite stays green, and pytest
lists these at the end of every run.

When one of these is fixed, its test starts passing; strict=True turns that into
a failure, as a reminder to move the test to the right file without the marker.
"""
import pytest

from helpers import review


def known_issue(reason):
    return pytest.mark.xfail(reason=reason, strict=True)


@known_issue("names go straight into URLs: a restaurant or dish name containing '/' "
             "can't be opened (the router treats it as a path separator). "
             "To be fixed by the route changes (ids/slugs in URLs).")
def test_restaurant_name_with_a_slash(client, alice):
    review(client, alice, dish_name="Ramen", restaurant_name="Bar / Grill")
    assert client.get("/restaurants/Bar%20%2F%20Grill/page", headers=alice.headers).status_code == 200
