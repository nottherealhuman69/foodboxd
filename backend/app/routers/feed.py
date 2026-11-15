"""The home feed."""

from fastapi import APIRouter, Depends

from app.core.db import get_db
from app.core.security import get_current_user
from app.services.posts import fork_source, post_tags, reposts_by, sort_at
from app.utils import serialise_meal, serialise_review, with_cursor

router = APIRouter()


@router.get("/feed")
def get_feed(email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT addressee_email FROM friendships
            WHERE requester_email = %s AND status = 'accepted'
        """, (email,))
        friend_emails = [r["addressee_email"] for r in cur.fetchall()]
        if not friend_emails:
            return []
        placeholders = ",".join(["%s"] * len(friend_emails))

        cur.execute(f"""
            SELECT
                r.id, r.user_email, r.dish_name, r.type, r.restaurant_name,
                r.recipe, r.recipe_owner_email, r.rating, r.review, r.logged_at,
                r.forked_from_id,
                COUNT(DISTINCT l.id) AS like_count,
                COUNT(DISTINCT c.id) AS comment_count,
                COALESCE(BOOL_OR(l.user_email = %s), FALSE) AS user_liked
            FROM dish_reviews r
            LEFT JOIN review_likes l ON l.review_id = r.id
            LEFT JOIN review_comments c ON c.review_id = r.id
            WHERE r.user_email IN ({placeholders}) AND r.meal_id IS NULL
            GROUP BY r.id
            ORDER BY r.logged_at DESC LIMIT 50
        """, [email] + friend_emails)

        review_rows = cur.fetchall()
        reviews = [{
            **serialise_review(r),
            "kind":          "review",
            "like_count":    int(r["like_count"]),
            "comment_count": int(r["comment_count"]),
            "user_liked":    bool(r["user_liked"]),
            "tagged":        post_tags(cur, "review", r["id"]),
            "forked_from":   fork_source(cur, "review", r["forked_from_id"]),
        } for r in review_rows]

        cur.execute(f"""
            SELECT m.*,
                   COUNT(DISTINCT l.id) AS like_count,
                   COUNT(DISTINCT c.id) AS comment_count,
                   COALESCE(BOOL_OR(l.user_email = %s), FALSE) AS user_liked
            FROM meals m
            LEFT JOIN meal_likes    l ON l.meal_id = m.id
            LEFT JOIN meal_comments c ON c.meal_id = m.id
            WHERE m.user_email IN ({placeholders})
            GROUP BY m.id
            ORDER BY m.logged_at DESC LIMIT 50
        """, [email] + friend_emails)
        meal_rows = cur.fetchall()

        meals = []
        for m in meal_rows:
            cur.execute("""
                SELECT id, dish_name, rating, review FROM dish_reviews
                WHERE meal_id = %s ORDER BY id ASC
            """, (m["id"],))
            dish_rows = cur.fetchall()
            meals.append({
                **serialise_meal(m, dish_rows),
                "like_count":    int(m["like_count"]),
                "comment_count": int(m["comment_count"]),
                "user_liked":    bool(m["user_liked"]),
                "tagged":        post_tags(cur, "meal", m["id"]),
                "forked_from":   fork_source(cur, "meal", m["forked_from_id"]),
            })
            reposts = reposts_by(cur, friend_emails, email)

    by_key = {}
    for item in reviews + meals + reposts:
        key = (item["kind"], item["id"])
        if key not in by_key or sort_at(item) > sort_at(by_key[key]):
            by_key[key] = item
    combined = sorted(by_key.values(), key=sort_at, reverse=True)
    return combined[:50]
