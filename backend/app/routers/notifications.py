"""Activity notifications."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends

from app.core.db import get_db
from app.core.security import get_current_user
from app.utils import username_from, with_cursor

router = APIRouter()


@router.get("/notifications/activity")
def get_activity_notifications(email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT 'like' AS type, 'review' AS target_type, l.id AS event_id, l.created_at,
                   r.id AS target_id, l.user_email AS actor_email,
                   r.dish_name AS subject, r.restaurant_name
            FROM review_likes l
            JOIN dish_reviews r ON r.id = l.review_id
            WHERE r.user_email = %s AND l.user_email != %s AND r.meal_id IS NULL

            UNION ALL

            SELECT 'comment', 'review', c.id, c.created_at,
                   r.id, c.user_email, r.dish_name, r.restaurant_name
            FROM review_comments c
            JOIN dish_reviews r ON r.id = c.review_id
            WHERE r.user_email = %s AND c.user_email != %s AND r.meal_id IS NULL

            UNION ALL

            SELECT 'like', 'meal', l.id, l.created_at,
                   m.id, l.user_email, m.title, m.restaurant_name
            FROM meal_likes l
            JOIN meals m ON m.id = l.meal_id
            WHERE m.user_email = %s AND l.user_email != %s

            UNION ALL

            SELECT 'comment', 'meal', c.id, c.created_at,
                   m.id, c.user_email, m.title, m.restaurant_name
            FROM meal_comments c
            JOIN meals m ON m.id = c.meal_id
            WHERE m.user_email = %s AND c.user_email != %s
            UNION ALL

            SELECT 'tag', 'review', t.id, t.created_at,
                  r.id, r.user_email, r.dish_name, r.restaurant_name
            FROM post_tags t
            JOIN dish_reviews r ON t.post_type = 'review' AND r.id = t.post_id
            WHERE t.tagged_email = %s

            UNION ALL

            SELECT 'tag', 'meal', t.id, t.created_at,
                      m.id, m.user_email, m.title, m.restaurant_name
            FROM post_tags t
            JOIN meals m ON t.post_type = 'meal' AND m.id = t.post_id
            WHERE t.tagged_email = %s
            ORDER BY created_at DESC
            LIMIT 50
        """, (email,) * 10)
        rows = cur.fetchall()
        cur.execute("SELECT post_type, post_id FROM post_reposts WHERE reposter_email = %s", (email,))
        reposted = {(r["post_type"], r["post_id"]) for r in cur.fetchall()}
    return [{
        "id":              r["event_id"],
        "type":            r["type"],
        "target_type":     r["target_type"],
        "target_id":       r["target_id"],
        "actor_email":     r["actor_email"],
        "actor_username":  username_from(r["actor_email"]),
        "subject":         r["subject"],
        "restaurant_name": r["restaurant_name"],
        "created_at":      r["created_at"],
        "user_reposted": (r["target_type"], r["target_id"]) in reposted if r["type"] == "tag" else None,
    } for r in rows]


@router.get("/notifications/unseen_count")
def get_unseen_count(since: Optional[datetime] = None,
                     email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT COUNT(*) AS count FROM friendships
            WHERE addressee_email = %s AND status = 'pending'
        """, (email,))
        pending_count = cur.fetchone()["count"]
 
        # NEW: pending group list invites
        cur.execute("""
            SELECT COUNT(*) AS count FROM group_list_members
            WHERE user_email = %s AND status = 'pending'
        """, (email,))
        group_invite_count = cur.fetchone()["count"]
 
        since_val = since or datetime(1970, 1, 1)
        cur.execute("""
            SELECT COUNT(*) AS count FROM (
                SELECT l.id FROM review_likes l
                JOIN dish_reviews r ON r.id = l.review_id
                WHERE r.user_email = %s AND l.user_email != %s
                  AND l.created_at > %s AND r.meal_id IS NULL

                UNION ALL

                SELECT c.id FROM review_comments c
                JOIN dish_reviews r ON r.id = c.review_id
                WHERE r.user_email = %s AND c.user_email != %s
                  AND c.created_at > %s AND r.meal_id IS NULL

                UNION ALL

                SELECT l.id FROM meal_likes l
                JOIN meals m ON m.id = l.meal_id
                WHERE m.user_email = %s AND l.user_email != %s AND l.created_at > %s

                UNION ALL

                SELECT c.id FROM meal_comments c
                JOIN meals m ON m.id = c.meal_id
                WHERE m.user_email = %s AND c.user_email != %s AND c.created_at > %s
                UNION ALL

                SELECT t.id FROM post_tags t
                JOIN dish_reviews r ON t.post_type = 'review' AND r.id = t.post_id
                WHERE t.tagged_email = %s AND t.created_at > %s

                UNION ALL

                SELECT t.id FROM post_tags t
                JOIN meals m ON t.post_type = 'meal' AND m.id = t.post_id
                WHERE t.tagged_email = %s AND t.created_at > %s
            ) combined
        """, (email, email, since_val) * 4 + (email, since_val) * 2)
        activity_count = cur.fetchone()["count"]
 
    return {"count": pending_count + group_invite_count + activity_count}
