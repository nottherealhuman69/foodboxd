"""Dish reviews: CRUD, likes and comments."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.core.db import get_db
from app.core.security import get_current_user
from app.schemas.posts import CommentCreate
from app.schemas.reviews import ReviewCreate, ReviewOut, ReviewUpdate
from app.services.posts import check_fork_source, delete_post_extras, find_my_fork, fork_source, post_tags, repost_state, reposts_by, set_post_tags, sort_at
from app.services.recipes import clean_ingredients, load_ingredients, set_ingredients
from app.services.validation import valid_rating
from app.utils import serialise_review, username_from, with_cursor

router = APIRouter()


@router.post("/reviews", status_code=201, response_model=ReviewOut)
def create_review(body: ReviewCreate, email: str = Depends(get_current_user), db=Depends(get_db)):
    if body.type not in ("restaurant", "homemade"):
        raise HTTPException(status_code=400, detail="type must be 'restaurant' or 'homemade'")
    if not valid_rating(body.rating):
        raise HTTPException(status_code=400, detail="rating must be between 0.5 and 5 in half-star steps")

    # Recipe tagging only applies to homemade dishes. NULL means it's your own recipe.
    recipe_owner = body.recipe_owner_email.strip() if body.recipe_owner_email else None
    if recipe_owner and body.type != "homemade":
        raise HTTPException(status_code=400, detail="Only homemade dishes can tag a recipe author")
    if recipe_owner == email:
        recipe_owner = None  # tagging yourself just means it's your own recipe
    ingredients = clean_ingredients(body.ingredients) if body.type == "homemade" else []
    with with_cursor(db) as cur:
        fork_id = check_fork_source(cur, "review", body.forked_from_id, email)
        if recipe_owner:
            cur.execute("SELECT id FROM users WHERE email = %s", (recipe_owner,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Tagged recipe author not found")
        cur.execute(
            """INSERT INTO dish_reviews (user_email, dish_name, type, restaurant_name, recipe, recipe_owner_email, rating, review, forked_from_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *""",
            (email, body.dish_name.strip(), body.type,
             body.restaurant_name.strip() if body.restaurant_name else None,
             body.recipe.strip() if body.recipe else None,
             recipe_owner,
             body.rating,
             body.review.strip() if body.review else None,
             fork_id)
        )
        row = cur.fetchone()
        if ingredients:
            set_ingredients(cur, row["id"], ingredients)
        set_post_tags(cur, "review", row["id"], email, body.tagged_emails)
        tagged = post_tags(cur, "review", row["id"])
        db.commit()   
    return {**dict(row), "tagged": tagged, "ingredients": load_ingredients(cur, row["id"])}


@router.get("/reviews", response_model=List[ReviewOut])
def get_reviews(email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT r.*,
                   COUNT(DISTINCT l.id) AS like_count,
                   COUNT(DISTINCT c.id) AS comment_count
            FROM dish_reviews r
            LEFT JOIN review_likes l ON l.review_id = r.id
            LEFT JOIN review_comments c ON c.review_id = r.id
            WHERE r.user_email = %s AND r.meal_id IS NULL
            GROUP BY r.id
            ORDER BY r.logged_at DESC
        """, (email,))
        rows = cur.fetchall()
        own = [{**dict(r), "tagged": post_tags(cur, "review", r["id"])} for r in rows]
        reposts = reposts_by(cur, [email], email, post_type="review", limit=200)
    return sorted(own + reposts, key=sort_at, reverse=True)


@router.delete("/reviews/{review_id}", status_code=204)
def delete_review(review_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT meal_id FROM dish_reviews WHERE id = %s AND user_email = %s", (review_id, email))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Review not found")
        if row["meal_id"] is not None:
            raise HTTPException(status_code=400, detail="This dish is part of a meal — delete the meal instead")
        delete_post_extras(cur, "review", review_id)
        cur.execute("DELETE FROM dish_reviews WHERE id = %s", (review_id,))
        db.commit()


@router.get("/reviews/{review_id}/detail")
def get_review_detail(review_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT r.*,
                   COUNT(DISTINCT l.id) AS like_count,
                   COUNT(DISTINCT c.id) AS comment_count,
                   COALESCE(BOOL_OR(l.user_email = %s), FALSE) AS user_liked
            FROM dish_reviews r
            LEFT JOIN review_likes l ON l.review_id = r.id
            LEFT JOIN review_comments c ON c.review_id = r.id
            WHERE r.id = %s
            GROUP BY r.id
        """, (email, review_id))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Review not found")
        tagged = post_tags(cur, "review", review_id)
        repost = repost_state(cur, "review", review_id, email)
        fork_src = fork_source(cur, "review", row["forked_from_id"])
        my_fork  = find_my_fork(cur, "review", review_id, email)
        ingredients = load_ingredients(cur, review_id)
    return {
        **serialise_review(row),
        "username":      username_from(row["user_email"]),
        "user_email":    row["user_email"],
        "like_count":    int(row["like_count"]),
        "comment_count": int(row["comment_count"]),
        "user_liked":    bool(row["user_liked"]),
        "meal_id":         row.get("meal_id"),
        "tagged":        tagged,
        **repost,
        "forked_from":    fork_src,
        "my_fork":        my_fork,
        "ingredients":    ingredients
    }


@router.patch("/reviews/{review_id}", response_model=ReviewOut)
def update_review(review_id: int, body: ReviewUpdate, email: str = Depends(get_current_user), db=Depends(get_db)):
    if body.type not in ("restaurant", "homemade"):
        raise HTTPException(status_code=400, detail="type must be 'restaurant' or 'homemade'")
    if not valid_rating(body.rating):
        raise HTTPException(status_code=400, detail="rating must be between 0.5 and 5 in half-star steps")

    recipe_owner = body.recipe_owner_email.strip() if body.recipe_owner_email else None
    if recipe_owner and body.type != "homemade":
        raise HTTPException(status_code=400, detail="Only homemade dishes can tag a recipe author")
    if recipe_owner == email:
        recipe_owner = None
    ingredients = clean_ingredients(body.ingredients) if body.type == "homemade" else []
    with with_cursor(db) as cur:
        cur.execute("SELECT meal_id FROM dish_reviews WHERE id = %s AND user_email = %s", (review_id, email))
        existing = cur.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Review not found")
        if existing["meal_id"] is not None:
            raise HTTPException(status_code=400, detail="This dish is part of a meal — edit the meal instead")
        if recipe_owner:
            cur.execute("SELECT id FROM users WHERE email = %s", (recipe_owner,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Tagged recipe author not found")
        cur.execute(
            """UPDATE dish_reviews
               SET dish_name = %s, type = %s, restaurant_name = %s, recipe = %s,
                   recipe_owner_email = %s, rating = %s, review = %s
               WHERE id = %s RETURNING *""",
            (body.dish_name.strip(), body.type,
             body.restaurant_name.strip() if body.restaurant_name else None,
             body.recipe.strip() if body.recipe else None,
             recipe_owner, body.rating,
             body.review.strip() if body.review else None,
             review_id)
        )
        row = cur.fetchone()
        if ingredients:
            set_ingredients(cur, row["id"], ingredients)
        set_post_tags(cur, "review", review_id, email, body.tagged_emails)
        tagged = post_tags(cur, "review", review_id)
        db.commit()
    return {**dict(row), "tagged": tagged, "ingredients": load_ingredients(cur, row["id"])}


@router.get("/reviews/{review_id}/likes")
def get_likes(review_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM dish_reviews WHERE id = %s", (review_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Review not found")
        cur.execute("""
            SELECT user_email, created_at FROM review_likes
            WHERE review_id = %s ORDER BY created_at DESC
        """, (review_id,))
        return [{
            "username":   username_from(r["user_email"]),
            "user_email": r["user_email"],
            "created_at": r["created_at"],
        } for r in cur.fetchall()]


@router.post("/reviews/{review_id}/like")
def toggle_like(review_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM dish_reviews WHERE id = %s", (review_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Review not found")
        cur.execute("SELECT id FROM review_likes WHERE review_id = %s AND user_email = %s", (review_id, email))
        if cur.fetchone():
            cur.execute("DELETE FROM review_likes WHERE review_id = %s AND user_email = %s", (review_id, email))
            liked = False
        else:
            cur.execute("INSERT INTO review_likes (review_id, user_email) VALUES (%s, %s)", (review_id, email))
            liked = True
        cur.execute("SELECT COUNT(*) AS count FROM review_likes WHERE review_id = %s", (review_id,))
        count = cur.fetchone()["count"]
        db.commit()
    return {"liked": liked, "like_count": int(count)}


@router.get("/reviews/{review_id}/comments")
def get_comments(review_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM dish_reviews WHERE id = %s", (review_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Review not found")
        cur.execute("""
            SELECT c.id, c.user_email, c.content, c.created_at, c.parent_id,
                   COUNT(cl.id) AS like_count,
                   COALESCE(BOOL_OR(cl.user_email = %s), FALSE) AS user_liked
            FROM review_comments c
            LEFT JOIN review_comment_likes cl ON cl.comment_id = c.id
            WHERE c.review_id = %s
            GROUP BY c.id
            ORDER BY c.created_at ASC
        """, (email, review_id))
        return [{"id": r["id"], "username": username_from(r["user_email"]), "user_email": r["user_email"],
                 "content": r["content"], "created_at": r["created_at"], "parent_id": r["parent_id"],
                 "like_count": int(r["like_count"]), "user_liked": bool(r["user_liked"])}
                for r in cur.fetchall()]


@router.post("/reviews/{review_id}/comments", status_code=201)
def add_comment(review_id: int, body: CommentCreate, email: str = Depends(get_current_user), db=Depends(get_db)):
    if not body.content.strip():
        raise HTTPException(status_code=400, detail="Comment cannot be empty")
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM dish_reviews WHERE id = %s", (review_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Review not found")
        if body.parent_id is not None:
            cur.execute("SELECT id FROM review_comments WHERE id = %s AND review_id = %s",
                        (body.parent_id, review_id))
            if not cur.fetchone():
                raise HTTPException(status_code=400, detail="Parent comment not found")
        cur.execute(
            "INSERT INTO review_comments (review_id, user_email, content, parent_id) VALUES (%s, %s, %s, %s) RETURNING id, created_at",
            (review_id, email, body.content.strip(), body.parent_id)
        )
        row = cur.fetchone()
        db.commit()
    return {"id": row["id"], "username": username_from(email), "user_email": email,
            "content": body.content.strip(), "created_at": row["created_at"],
            "parent_id": body.parent_id, "like_count": 0, "user_liked": False}


@router.delete("/reviews/{review_id}/comments/{comment_id}", status_code=204)
def delete_comment(review_id: int, comment_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM review_comments WHERE id = %s AND review_id = %s AND user_email = %s",
                    (comment_id, review_id, email))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Comment not found")
        cur.execute("DELETE FROM review_comments WHERE id = %s", (comment_id,))
        db.commit()


@router.get("/reviews/all")
def get_all_reviews(email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT r.*, u.email AS user_email
            FROM dish_reviews r JOIN users u ON u.email = r.user_email
            ORDER BY r.logged_at DESC
        """)
        return [serialise_review(r) for r in cur.fetchall()]
