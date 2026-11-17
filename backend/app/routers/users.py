"""Other users: search and profile data."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.core.db import get_db
from app.core.security import get_current_user
from app.schemas.reviews import ReviewOut
from app.services.posts import post_tags, reposts_by, sort_at
from app.services.privacy import can_view_author
from app.utils import serialise_meal, username_from, with_cursor

router = APIRouter()


@router.get("/users/search")
def search_users(q: str = "", email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT u.email, u.is_private, COUNT(r.id) AS review_count
            FROM users u
            LEFT JOIN dish_reviews r ON r.user_email = u.email
            WHERE u.email != %s AND u.email ILIKE %s
            GROUP BY u.email, u.is_private
            ORDER BY review_count DESC
            LIMIT 20
        """, (email, f"%{q}%"))
        users = cur.fetchall()

        result = []
        for u in users:
            # The follow button reflects only my outbound follow of this user.
            cur.execute("""
                SELECT status FROM friendships
                WHERE requester_email = %s AND addressee_email = %s
            """, (email, u["email"]))
            rel = cur.fetchone()

            if   rel is None:                  status = None
            elif rel["status"] == "accepted":  status = "following"
            elif rel["status"] == "pending":   status = "pending_sent"
            else:                              status = None   # declined

            result.append({
                "email":             u["email"],
                "username":          username_from(u["email"]),
                "review_count":      u["review_count"],
                "is_private":        bool(u["is_private"]),
                "friendship_status": status,
            })
    return result


@router.get("/users/{user_email}/reviews", response_model=List[ReviewOut])
def get_user_reviews(user_email: str, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM users WHERE email = %s", (user_email,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="User not found")
        if not can_view_author(cur, email, user_email):
            return []      # private account the caller doesn't follow
        cur.execute("""SELECT * FROM dish_reviews
                       WHERE user_email = %s AND meal_id IS NULL
                       ORDER BY logged_at DESC""", (user_email,))
        own = [{**dict(r), "tagged": post_tags(cur, "review", r["id"])} for r in cur.fetchall()]
        reposts = reposts_by(cur, [user_email], email, post_type="review", limit=200)
    return sorted(own + reposts, key=sort_at, reverse=True)


@router.get("/users/{user_email}/friends")
def get_user_friends(user_email: str, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM users WHERE email = %s", (user_email,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="User not found")

        cur.execute("""
            SELECT f.addressee_email AS friend_email, COUNT(r.id) AS review_count
            FROM friendships f
            LEFT JOIN dish_reviews r ON r.user_email = f.addressee_email
            WHERE f.requester_email = %s AND f.status = 'accepted'
            GROUP BY f.addressee_email
        """, (user_email,))
        rows = cur.fetchall()
    return [{"email": r["friend_email"], "username": username_from(r["friend_email"]), "review_count": r["review_count"]} for r in rows]


@router.get("/users/{user_email}/lists")
def get_user_public_lists(user_email: str, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM users WHERE email = %s", (user_email,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="User not found")
        cur.execute("""
            SELECT cl.id, cl.name, cl.is_public, cl.created_at,
                   COUNT(li.id) AS item_count
            FROM custom_lists cl
            LEFT JOIN list_items li ON li.list_id = cl.id
            WHERE cl.user_email = %s AND cl.is_public = TRUE
            GROUP BY cl.id
            ORDER BY cl.created_at DESC
        """, (user_email,))
        return cur.fetchall()


@router.get("/users/{user_email}/group-lists")
def get_public_group_lists(user_email: str, email: str = Depends(get_current_user),
                           db=Depends(get_db)):
    """Public group lists this user is an accepted member of."""
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT gl.id, gl.name, gl.owner_email, gl.is_public, gl.created_at,
                   (SELECT COUNT(*) FROM group_list_members m
                     WHERE m.group_list_id = gl.id AND m.status = 'accepted') AS member_count,
                   (SELECT COUNT(*) FROM group_list_items i
                     WHERE i.group_list_id = gl.id) AS item_count
            FROM group_lists gl
            JOIN group_list_members me ON me.group_list_id = gl.id
            WHERE me.user_email = %s AND me.status = 'accepted' AND gl.is_public = TRUE
            ORDER BY gl.created_at DESC
        """, (user_email,))
        rows = cur.fetchall()
    return [{**dict(r), "owner_username": username_from(r["owner_email"])} for r in rows]


@router.get("/users/{user_email}/meals")
def get_user_meals(user_email: str, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        if not can_view_author(cur, email, user_email):
            return []      # private account the caller doesn't follow
        cur.execute("SELECT * FROM meals WHERE user_email = %s ORDER BY logged_at DESC", (user_email,))
        meals = cur.fetchall()
        out = []
        for m in meals:
            cur.execute("""
                SELECT id, dish_name, rating, review FROM dish_reviews
                WHERE meal_id = %s ORDER BY id ASC
            """, (m["id"],))
            dish_rows = cur.fetchall()
            out.append({**serialise_meal(m, dish_rows), "tagged": post_tags(cur, "meal", m["id"])})
        out += reposts_by(cur, [user_email], email, post_type="meal", limit=200)
    out.sort(key=sort_at, reverse=True)
    return out
