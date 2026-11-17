"""Meals (multi-dish posts): CRUD, likes and comments."""

from fastapi import APIRouter, Depends, HTTPException

from app.core.db import get_db
from app.core.security import get_current_user
from app.schemas.meals import MealCreate
from app.schemas.posts import CommentCreate
from app.services.meals import load_meal
from app.services.privacy import require_visible_meal
from app.services.posts import check_fork_source, delete_post_extras, find_my_fork, fork_source, post_tags, repost_state, reposts_by, set_post_tags, sort_at
from app.services.validation import valid_rating
from app.utils import serialise_meal, username_from, with_cursor

router = APIRouter()


@router.post("/meals", status_code=201)
def create_meal(body: MealCreate, email: str = Depends(get_current_user), db=Depends(get_db)):
    restaurant = body.restaurant_name.strip()
    if not restaurant:
        raise HTTPException(status_code=400, detail="Restaurant is required")
    if not valid_rating(body.rating):
        raise HTTPException(status_code=400, detail="Overall rating must be between 0.5 and 5 in half-star steps")

    dishes, seen = [], set()
    for d in body.dishes:
        name = d.dish_name.strip()
        if not name:
            continue
        if name.lower() in seen:
            raise HTTPException(status_code=400, detail=f"'{name}' is listed twice")
        if not valid_rating(d.rating):
            raise HTTPException(status_code=400, detail=f"Rating for '{name}' must be between 0.5 and 5 in half-star steps")
        seen.add(name.lower())
        dishes.append((name, d.rating, (d.review or "").strip() or None))

    if not dishes:
        raise HTTPException(status_code=400, detail="A meal needs at least one rated dish")

    try:
        with with_cursor(db) as cur:
            fork_id = check_fork_source(cur, "meal", body.forked_from_id, email)
            cur.execute("""
                INSERT INTO meals (user_email, restaurant_name, title, rating, review, forked_from_id)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING *
            """, (email, restaurant, (body.title or "").strip() or None,
                  body.rating, (body.review or "").strip() or None, fork_id))
            meal = cur.fetchone()

            dish_rows = []
            for name, dish_rating, note in dishes:
                cur.execute("""
                    INSERT INTO dish_reviews
                        (user_email, dish_name, type, restaurant_name, rating, review, meal_id)
                    VALUES (%s, %s, 'restaurant', %s, %s, %s, %s)
                    RETURNING id, dish_name, rating, review
                """, (email, name, restaurant, dish_rating, note, meal["id"]))
                dish_rows.append(cur.fetchone())
            set_post_tags(cur, "meal", meal["id"], email, body.tagged_emails)
            tagged = post_tags(cur, "meal", meal["id"])
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not save meal")

    return {**serialise_meal(meal, dish_rows), "tagged": tagged}


@router.get("/meals")
def get_my_meals(email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT * FROM meals WHERE user_email = %s ORDER BY logged_at DESC", (email,))
        meals = cur.fetchall()
        out = []
        for m in meals:
            cur.execute("""
                SELECT id, dish_name, rating, review FROM dish_reviews
                WHERE meal_id = %s ORDER BY id ASC
            """, (m["id"],))
            dish_rows = cur.fetchall()
            out.append({**serialise_meal(m, dish_rows), "tagged": post_tags(cur, "meal", m["id"])})
        out += reposts_by(cur, [email], email, post_type="meal", limit=200)
    out.sort(key=sort_at, reverse=True)
    return out


@router.get("/meals/{meal_id}")
def get_meal(meal_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        require_visible_meal(cur, meal_id, email)
        meal, dish_rows = load_meal(cur, meal_id)
        tagged = post_tags(cur, "meal", meal_id)
    return {**serialise_meal(meal, dish_rows), "tagged": tagged}


@router.delete("/meals/{meal_id}", status_code=204)
def delete_meal(meal_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM meals WHERE id = %s AND user_email = %s", (meal_id, email))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Meal not found")
        delete_post_extras(cur, "meal", meal_id)
        cur.execute("DELETE FROM meals WHERE id = %s", (meal_id,))
        db.commit()


@router.patch("/meals/{meal_id}")
def update_meal(meal_id: int, body: MealCreate, email: str = Depends(get_current_user), db=Depends(get_db)):
    restaurant = body.restaurant_name.strip()
    if not restaurant:
        raise HTTPException(status_code=400, detail="Restaurant is required")
    if not valid_rating(body.rating):
        raise HTTPException(status_code=400, detail="Overall rating must be between 0.5 and 5 in half-star steps")

    dishes, seen = [], set()
    for d in body.dishes:
        name = d.dish_name.strip()
        if not name:
            continue
        if name.lower() in seen:
            raise HTTPException(status_code=400, detail=f"'{name}' is listed twice")
        if not valid_rating(d.rating):
            raise HTTPException(status_code=400, detail=f"Rating for '{name}' must be between 0.5 and 5 in half-star steps")
        seen.add(name.lower())
        dishes.append((d.id, name, d.rating, (d.review or "").strip() or None))
    if not dishes:
        raise HTTPException(status_code=400, detail="A meal needs at least one rated dish")

    try:
        with with_cursor(db) as cur:
            cur.execute("SELECT id FROM meals WHERE id = %s AND user_email = %s", (meal_id, email))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Meal not found")

            cur.execute("""
                UPDATE meals SET restaurant_name = %s, title = %s, rating = %s, review = %s
                WHERE id = %s RETURNING *
            """, (restaurant, (body.title or "").strip() or None,
                  body.rating, (body.review or "").strip() or None, meal_id))
            meal = cur.fetchone()

            cur.execute("SELECT id FROM dish_reviews WHERE meal_id = %s", (meal_id,))
            existing_ids = {r["id"] for r in cur.fetchall()}
            kept_ids = set()

            for dish_id, name, dish_rating, note in dishes:
                if dish_id in existing_ids:
                    cur.execute("""
                        UPDATE dish_reviews
                        SET dish_name = %s, restaurant_name = %s, rating = %s, review = %s
                        WHERE id = %s
                    """, (name, restaurant, dish_rating, note, dish_id))
                    kept_ids.add(dish_id)
                else:
                    cur.execute("""
                        INSERT INTO dish_reviews
                            (user_email, dish_name, type, restaurant_name, rating, review, meal_id)
                        VALUES (%s, %s, 'restaurant', %s, %s, %s, %s)
                    """, (email, name, restaurant, dish_rating, note, meal_id))

            removed = existing_ids - kept_ids
            if removed:
                cur.execute("DELETE FROM dish_reviews WHERE id = ANY(%s)", (list(removed),))

            set_post_tags(cur, "meal", meal_id, email, body.tagged_emails)
            _, dish_rows = load_meal(cur, meal_id)
            tagged = post_tags(cur, "meal", meal_id)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not update meal")

    return {**serialise_meal(meal, dish_rows), "tagged": tagged}


@router.get("/meals/{meal_id}/detail")
def get_meal_detail(meal_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT m.*,
                   COUNT(DISTINCT l.id) AS like_count,
                   COUNT(DISTINCT c.id) AS comment_count,
                   COALESCE(BOOL_OR(l.user_email = %s), FALSE) AS user_liked
            FROM meals m
            LEFT JOIN meal_likes l ON l.meal_id = m.id
            LEFT JOIN meal_comments c ON c.meal_id = m.id
            WHERE m.id = %s
            GROUP BY m.id
        """, (email, meal_id))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Meal not found")
        require_visible_meal(cur, meal_id, email)
        cur.execute("""
            SELECT id, dish_name, rating, review FROM dish_reviews
            WHERE meal_id = %s ORDER BY id ASC
        """, (meal_id,))
        dish_rows = cur.fetchall()
        tagged = post_tags(cur, "meal", meal_id)
        repost = repost_state(cur, "meal", meal_id, email)
        fork_src = fork_source(cur, "meal", row["forked_from_id"])
        my_fork = find_my_fork(cur, "meal", meal_id, email)  
    return {
        **serialise_meal(row, dish_rows),
        "like_count":    int(row["like_count"]),
        "comment_count": int(row["comment_count"]),
        "user_liked":    bool(row["user_liked"]),
        "tagged":        tagged,
        **repost,
        "forked_from":   fork_src,
        "my_fork":       my_fork,
    }


@router.post("/meals/{meal_id}/like")
def toggle_meal_like(meal_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        require_visible_meal(cur, meal_id, email)
        cur.execute("SELECT id FROM meal_likes WHERE meal_id = %s AND user_email = %s", (meal_id, email))
        if cur.fetchone():
            cur.execute("DELETE FROM meal_likes WHERE meal_id = %s AND user_email = %s", (meal_id, email))
            liked = False
        else:
            cur.execute("INSERT INTO meal_likes (meal_id, user_email) VALUES (%s, %s)", (meal_id, email))
            liked = True
        cur.execute("SELECT COUNT(*) AS count FROM meal_likes WHERE meal_id = %s", (meal_id,))
        count = cur.fetchone()["count"]
        db.commit()
    return {"liked": liked, "like_count": int(count)}


@router.get("/meals/{meal_id}/likes")
def get_meal_likes(meal_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        require_visible_meal(cur, meal_id, email)
        cur.execute("""
            SELECT user_email, created_at FROM meal_likes
            WHERE meal_id = %s ORDER BY created_at DESC
        """, (meal_id,))
        return [{
            "username":   username_from(r["user_email"]),
            "user_email": r["user_email"],
            "created_at": r["created_at"],
        } for r in cur.fetchall()]


@router.get("/meals/{meal_id}/comments")
def get_meal_comments(meal_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        require_visible_meal(cur, meal_id, email)
        cur.execute("""
            SELECT c.id, c.user_email, c.content, c.created_at, c.parent_id,
                   COUNT(cl.id) AS like_count,
                   COALESCE(BOOL_OR(cl.user_email = %s), FALSE) AS user_liked
            FROM meal_comments c
            LEFT JOIN meal_comment_likes cl ON cl.comment_id = c.id
            WHERE c.meal_id = %s
            GROUP BY c.id
            ORDER BY c.created_at ASC
        """, (email, meal_id))
        return [{
            "id":         r["id"],
            "username":   username_from(r["user_email"]),
            "user_email": r["user_email"],
            "content":    r["content"],
            "created_at": r["created_at"],
            "parent_id":  r["parent_id"],
            "like_count": int(r["like_count"]),
            "user_liked": bool(r["user_liked"]),
        } for r in cur.fetchall()]


@router.post("/meals/{meal_id}/comments", status_code=201)
def add_meal_comment(meal_id: int, body: CommentCreate,
                     email: str = Depends(get_current_user), db=Depends(get_db)):
    content = body.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Comment cannot be empty")
    with with_cursor(db) as cur:
        require_visible_meal(cur, meal_id, email)
        if body.parent_id is not None:
            cur.execute("SELECT id FROM meal_comments WHERE id = %s AND meal_id = %s",
                        (body.parent_id, meal_id))
            if not cur.fetchone():
                raise HTTPException(status_code=400, detail="Parent comment not found")
        cur.execute("""
            INSERT INTO meal_comments (meal_id, user_email, content, parent_id)
            VALUES (%s, %s, %s, %s) RETURNING id, created_at
        """, (meal_id, email, content, body.parent_id))
        row = cur.fetchone()
        db.commit()
    return {"id": row["id"], "username": username_from(email), "user_email": email,
            "content": content, "created_at": row["created_at"],
            "parent_id": body.parent_id, "like_count": 0, "user_liked": False}


@router.delete("/meals/{meal_id}/comments/{comment_id}", status_code=204)
def delete_meal_comment(meal_id: int, comment_id: int,
                        email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM meal_comments WHERE id = %s AND meal_id = %s AND user_email = %s",
                    (comment_id, meal_id, email))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Comment not found")
        cur.execute("DELETE FROM meal_comments WHERE id = %s", (comment_id,))
        db.commit()
