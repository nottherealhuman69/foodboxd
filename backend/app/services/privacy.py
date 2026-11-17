"""Who can see whose posts.

Rule (what Settings promises users): a private account's reviews and meals are
visible only to the author, to followers they've approved, and to people tagged
in that particular post. Public accounts' posts are visible to everyone.
"""
from fastapi import HTTPException

from app.services.social import is_following


def visible_author_sql(author_col: str) -> str:
    """SQL condition: posts by `author_col` are visible to the viewer.
    Needs the viewer's email passed TWICE as parameters, in this order."""
    return f"""(
        {author_col} = %s
        OR NOT EXISTS (SELECT 1 FROM users pu WHERE pu.email = {author_col} AND pu.is_private)
        OR EXISTS (SELECT 1 FROM friendships pf
                   WHERE pf.requester_email = %s AND pf.addressee_email = {author_col}
                     AND pf.status = 'accepted')
    )"""


def can_view_author(cur, viewer: str, author: str) -> bool:
    if viewer == author:
        return True
    cur.execute("SELECT is_private FROM users WHERE email = %s", (author,))
    row = cur.fetchone()
    if not row or not row["is_private"]:
        return True
    return is_following(cur, viewer, author)


def is_tagged(cur, viewer: str, post_type: str, post_id: int) -> bool:
    cur.execute("SELECT 1 FROM post_tags WHERE post_type = %s AND post_id = %s AND tagged_email = %s",
                (post_type, post_id, viewer))
    return cur.fetchone() is not None


def can_view_post(cur, viewer: str, post_type: str, post_id: int, author: str) -> bool:
    return can_view_author(cur, viewer, author) or is_tagged(cur, viewer, post_type, post_id)


def require_visible_review(cur, review_id: int, viewer: str) -> dict:
    """The review row (id, user_email, meal_id), or 404 if it doesn't exist or the
    viewer may not see it. A dish inside a meal follows the meal's tags."""
    cur.execute("SELECT id, user_email, meal_id FROM dish_reviews WHERE id = %s", (review_id,))
    row = cur.fetchone()
    if row:
        post_type, post_id = ("meal", row["meal_id"]) if row["meal_id"] else ("review", row["id"])
        if can_view_post(cur, viewer, post_type, post_id, row["user_email"]):
            return row
    raise HTTPException(status_code=404, detail="Review not found")


def require_visible_meal(cur, meal_id: int, viewer: str) -> dict:
    """The meal row (id, user_email), or 404 if it doesn't exist or the viewer may not see it."""
    cur.execute("SELECT id, user_email FROM meals WHERE id = %s", (meal_id,))
    row = cur.fetchone()
    if row and can_view_post(cur, viewer, "meal", meal_id, row["user_email"]):
        return row
    raise HTTPException(status_code=404, detail="Meal not found")
