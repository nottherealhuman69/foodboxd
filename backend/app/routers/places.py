"""Restaurants, dishes, recipes and place search.

Names are matched case-insensitively ("Ichiran" == "ichiran") and shown with their
most common spelling. Only reviews the caller is allowed to see are counted
(see services/privacy.py), so a private account's reviews never leak through here.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.core.db import get_db
from app.core.security import get_current_user
from app.services.privacy import visible_author_sql
from app.services.recipes import load_ingredients
from app.utils import serialise_review, username_from, with_cursor

router = APIRouter()

VISIBLE = visible_author_sql("r.user_email")          # needs (viewer, viewer)
SAME_RESTAURANT = "LOWER(r.restaurant_name) = LOWER(%s)"
SAME_DISH = "LOWER(r.dish_name) = LOWER(%s)"


@router.get("/restaurants")
def get_restaurants(email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute(f"""
            SELECT MODE() WITHIN GROUP (ORDER BY r.restaurant_name) AS name
            FROM dish_reviews r
            WHERE r.type = 'restaurant' AND r.restaurant_name IS NOT NULL AND {VISIBLE}
            GROUP BY LOWER(r.restaurant_name)
            ORDER BY name ASC
        """, (email, email))
        return [r["name"] for r in cur.fetchall()]


@router.get("/restaurants/{restaurant_name}/dishes")
def get_restaurant_dishes(restaurant_name: str, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute(f"""
            SELECT MODE() WITHIN GROUP (ORDER BY r.dish_name) AS name
            FROM dish_reviews r
            WHERE r.type = 'restaurant' AND {SAME_RESTAURANT} AND {VISIBLE}
            GROUP BY LOWER(r.dish_name)
            ORDER BY name ASC
        """, (restaurant_name, email, email))
        return [r["name"] for r in cur.fetchall()]


@router.get("/restaurants/{restaurant_name}/page")
def get_restaurant_page(restaurant_name: str, email: str = Depends(get_current_user), db=Depends(get_db)):
    where = f"r.type = 'restaurant' AND {SAME_RESTAURANT} AND {VISIBLE}"
    params = (restaurant_name, email, email)
    with with_cursor(db) as cur:
        cur.execute(f"""
            SELECT MODE() WITHIN GROUP (ORDER BY r.restaurant_name) AS restaurant_name,
                   COUNT(*) AS total_reviews,
                   ROUND(AVG(r.rating)::numeric, 1) AS avg_rating,
                   COUNT(DISTINCT LOWER(r.dish_name)) AS total_dishes,
                   MIN(r.logged_at) AS first_logged,
                   (ARRAY_AGG(r.user_email ORDER BY r.logged_at ASC))[1] AS created_by
            FROM dish_reviews r WHERE {where}
        """, params)
        stats = cur.fetchone()
        if not stats["total_reviews"]:
            raise HTTPException(status_code=404, detail="Restaurant not found")

        cur.execute(f"""
            SELECT MODE() WITHIN GROUP (ORDER BY r.dish_name) AS dish_name,
                   COUNT(*) AS review_count, ROUND(AVG(r.rating)::numeric, 1) AS avg_rating
            FROM dish_reviews r WHERE {where}
            GROUP BY LOWER(r.dish_name)
            ORDER BY avg_rating DESC, review_count DESC
        """, params)
        dishes = cur.fetchall()

        cur.execute(f"""
            SELECT r.id, r.user_email, r.dish_name, r.rating, r.review, r.logged_at, r.meal_id
            FROM dish_reviews r WHERE {where}
            ORDER BY r.logged_at DESC
        """, params)
        reviews = cur.fetchall()

    return {
        "restaurant_name": stats["restaurant_name"],
        "total_reviews":   stats["total_reviews"],
        "avg_rating":      float(stats["avg_rating"]),
        "total_dishes":    stats["total_dishes"],
        "created_by":      username_from(stats["created_by"]),
        "created_by_email": stats["created_by"],
        "first_logged":    stats["first_logged"],
        "dishes":  [{"dish_name": d["dish_name"], "review_count": d["review_count"], "avg_rating": float(d["avg_rating"])} for d in dishes],
        "reviews": [serialise_review(r) for r in reviews],
    }


@router.get("/dishes")
def get_all_dishes(email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute(f"""
            SELECT MODE() WITHIN GROUP (ORDER BY r.dish_name)       AS dish_name,
                   MODE() WITHIN GROUP (ORDER BY r.restaurant_name) AS restaurant_name,
                   COUNT(*) AS review_count,
                   ROUND(AVG(r.rating)::numeric, 1) AS avg_rating,
                   MIN(r.logged_at) AS first_logged,
                   (ARRAY_AGG(r.user_email ORDER BY r.logged_at ASC))[1] AS created_by
            FROM dish_reviews r
            WHERE r.type = 'restaurant' AND r.restaurant_name IS NOT NULL AND {VISIBLE}
            GROUP BY LOWER(r.dish_name), LOWER(r.restaurant_name)
            ORDER BY review_count DESC, first_logged DESC
        """, (email, email))
        rows = cur.fetchall()
    return [{"dish_name": r["dish_name"], "restaurant_name": r["restaurant_name"],
             "review_count": r["review_count"], "avg_rating": float(r["avg_rating"]),
             "created_by": username_from(r["created_by"]), "created_by_email": r["created_by"]} for r in rows]


@router.get("/search/dishes-restaurants")
def search_dishes_restaurants(q: str = "", item_type: str = "dish",
                              email: str = Depends(get_current_user), db=Depends(get_db)):
    if not q.strip():
        return []
    pattern = f"%{q.strip()}%"
    with with_cursor(db) as cur:
        if item_type == "restaurant":
            cur.execute(f"""
                SELECT MODE() WITHIN GROUP (ORDER BY r.restaurant_name) AS name
                FROM dish_reviews r
                WHERE r.type = 'restaurant' AND r.restaurant_name IS NOT NULL
                  AND r.restaurant_name ILIKE %s AND {VISIBLE}
                GROUP BY LOWER(r.restaurant_name)
                ORDER BY name
                LIMIT 10
            """, (pattern, email, email))
            return [{"name": r["name"], "restaurant_name": None} for r in cur.fetchall()]

        cur.execute(f"""
            SELECT MODE() WITHIN GROUP (ORDER BY r.dish_name)       AS dish_name,
                   MODE() WITHIN GROUP (ORDER BY r.restaurant_name) AS restaurant_name
            FROM dish_reviews r
            WHERE r.type = 'restaurant' AND r.restaurant_name IS NOT NULL
              AND (r.dish_name ILIKE %s OR r.restaurant_name ILIKE %s) AND {VISIBLE}
            GROUP BY LOWER(r.dish_name), LOWER(r.restaurant_name)
            ORDER BY dish_name
            LIMIT 10
        """, (pattern, pattern, email, email))
        return [{"name": r["dish_name"], "restaurant_name": r["restaurant_name"]} for r in cur.fetchall()]


@router.get("/dishes/{dish_name}/restaurant/{restaurant_name}")
def get_dish_page(dish_name: str, restaurant_name: str, email: str = Depends(get_current_user), db=Depends(get_db)):
    where = f"r.type = 'restaurant' AND {SAME_DISH} AND {SAME_RESTAURANT} AND {VISIBLE}"
    params = (dish_name, restaurant_name, email, email)
    with with_cursor(db) as cur:
        cur.execute(f"""
            SELECT MODE() WITHIN GROUP (ORDER BY r.dish_name)       AS dish_name,
                   MODE() WITHIN GROUP (ORDER BY r.restaurant_name) AS restaurant_name,
                   COUNT(*) AS review_count,
                   ROUND(AVG(r.rating)::numeric, 1) AS avg_rating,
                   MIN(r.logged_at) AS first_logged,
                   (ARRAY_AGG(r.user_email ORDER BY r.logged_at ASC))[1] AS created_by
            FROM dish_reviews r WHERE {where}
        """, params)
        stats = cur.fetchone()
        if not stats["review_count"]:
            raise HTTPException(status_code=404, detail="Dish not found")

        cur.execute(f"""
            SELECT r.id, r.user_email, r.rating, r.review, r.logged_at, r.meal_id
            FROM dish_reviews r WHERE {where}
            ORDER BY r.logged_at DESC
        """, params)
        reviews = cur.fetchall()

    return {
        "dish_name":        stats["dish_name"],
        "restaurant_name":  stats["restaurant_name"],
        "review_count":     stats["review_count"],
        "avg_rating":       float(stats["avg_rating"]),
        "created_by":       username_from(stats["created_by"]),
        "created_by_email": stats["created_by"],
        "first_logged":     stats["first_logged"],
        "reviews": [serialise_review(r) for r in reviews],
    }


@router.get("/recipes/page")
def get_recipe_page(dish_name: str, owner: str, email: str = Depends(get_current_user), db=Depends(get_db)):
    where = f"""r.type = 'homemade' AND {SAME_DISH}
                AND COALESCE(r.recipe_owner_email, r.user_email) = %s AND {VISIBLE}"""
    params = (dish_name, owner, email, email)
    with with_cursor(db) as cur:
        cur.execute(f"""
            SELECT MIN(r.dish_name) AS dish_name,
                   COUNT(*) AS review_count,
                   ROUND(AVG(r.rating)::numeric, 1) AS avg_rating,
                   MIN(r.logged_at) AS first_logged
            FROM dish_reviews r WHERE {where}
        """, params)
        stats = cur.fetchone()
        if not stats["review_count"]:
            raise HTTPException(status_code=404, detail="Recipe not found")

        # The recipe text: prefer the owner's own latest version, else anyone's
        cur.execute(f"""
            SELECT r.id, r.recipe FROM dish_reviews r
            WHERE {where} AND (COALESCE(r.recipe, '') <> '' OR EXISTS
                  (SELECT 1 FROM recipe_ingredients ri WHERE ri.review_id = r.id))
            ORDER BY (r.user_email = %s) DESC, r.logged_at DESC
            LIMIT 1
        """, params + (owner,))
        recipe_row = cur.fetchone()
        ingredients = load_ingredients(cur, recipe_row["id"]) if recipe_row else []

        cur.execute(f"""
            SELECT r.id, r.user_email, r.rating, r.review, r.logged_at, r.meal_id
            FROM dish_reviews r WHERE {where}
            ORDER BY r.logged_at DESC
        """, params)
        reviews = cur.fetchall()

    return {
        "dish_name":        stats["dish_name"],
        "restaurant_name":  None,
        "review_count":     stats["review_count"],
        "avg_rating":       float(stats["avg_rating"]),
        "created_by":       username_from(owner),
        "created_by_email": owner,
        "first_logged":     stats["first_logged"],
        "recipe":           (recipe_row["recipe"] or "") if recipe_row else "",
        "ingredients":      ingredients,
        "reviews":          [serialise_review(r) for r in reviews],
    }
