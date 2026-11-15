"""Restaurants, dishes, recipes and place search."""

from fastapi import APIRouter, Depends, HTTPException

from app.core.db import get_db
from app.core.security import get_current_user
from app.services.recipes import load_ingredients
from app.utils import serialise_review, username_from, with_cursor

router = APIRouter()


@router.get("/restaurants")
def get_restaurants(email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT DISTINCT restaurant_name FROM dish_reviews
            WHERE type = 'restaurant' AND restaurant_name IS NOT NULL
            ORDER BY restaurant_name ASC
        """)
        return [r["restaurant_name"] for r in cur.fetchall()]


@router.get("/restaurants/{restaurant_name}/dishes")
def get_restaurant_dishes(restaurant_name: str, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT DISTINCT dish_name FROM dish_reviews
            WHERE type = 'restaurant' AND restaurant_name ILIKE %s
            ORDER BY dish_name ASC
        """, (restaurant_name,))
        return [r["dish_name"] for r in cur.fetchall()]


@router.get("/restaurants/{restaurant_name}/page")
def get_restaurant_page(restaurant_name: str, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT restaurant_name,
                   COUNT(*) AS total_reviews,
                   ROUND(AVG(rating)::numeric, 1) AS avg_rating,
                   COUNT(DISTINCT dish_name) AS total_dishes,
                   MIN(logged_at) AS first_logged,
                   (ARRAY_AGG(user_email ORDER BY logged_at ASC))[1] AS created_by
            FROM dish_reviews
            WHERE restaurant_name ILIKE %s AND type = 'restaurant'
            GROUP BY restaurant_name
        """, (restaurant_name,))
        stats = cur.fetchone()
        if not stats:
            raise HTTPException(status_code=404, detail="Restaurant not found")

        cur.execute("""
            SELECT dish_name, COUNT(*) AS review_count, ROUND(AVG(rating)::numeric,1) AS avg_rating
            FROM dish_reviews WHERE restaurant_name ILIKE %s AND type = 'restaurant'
            GROUP BY dish_name ORDER BY avg_rating DESC, review_count DESC
        """, (restaurant_name,))
        dishes = cur.fetchall()

        cur.execute("""
            SELECT id, user_email, dish_name, rating, review, logged_at, meal_id
            FROM dish_reviews WHERE restaurant_name ILIKE %s AND type = 'restaurant'
            ORDER BY logged_at DESC
        """, (restaurant_name,))
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
        cur.execute("""
            SELECT dish_name, restaurant_name,
                   COUNT(*) AS review_count,
                   ROUND(AVG(rating)::numeric, 1) AS avg_rating,
                   MIN(logged_at) AS first_logged,
                   (ARRAY_AGG(user_email ORDER BY logged_at ASC))[1] AS created_by
            FROM dish_reviews
            WHERE type = 'restaurant' AND restaurant_name IS NOT NULL
            GROUP BY dish_name, restaurant_name
            ORDER BY review_count DESC, first_logged DESC
        """)
        rows = cur.fetchall()
    return [{"dish_name": r["dish_name"], "restaurant_name": r["restaurant_name"],
             "review_count": r["review_count"], "avg_rating": float(r["avg_rating"]),
             "created_by": username_from(r["created_by"]), "created_by_email": r["created_by"]} for r in rows]


@router.get("/search/dishes-restaurants")
def search_dishes_restaurants(q: str = "", item_type: str = "dish",
                              _email: str = Depends(get_current_user), db=Depends(get_db)):
    if not q.strip():
        return []
    pattern = f"%{q.strip()}%"
    with with_cursor(db) as cur:
        if item_type == "restaurant":
            cur.execute("""
                SELECT DISTINCT restaurant_name
                FROM dish_reviews
                WHERE type = 'restaurant'
                  AND restaurant_name IS NOT NULL
                  AND restaurant_name ILIKE %s
                ORDER BY restaurant_name
                LIMIT 10
            """, (pattern,))
            rows = cur.fetchall()
            return [{"name": r["restaurant_name"], "restaurant_name": None} for r in rows]
        else:
            cur.execute("""
                SELECT DISTINCT dish_name, restaurant_name
                FROM dish_reviews
                WHERE type = 'restaurant'
                  AND restaurant_name IS NOT NULL
                  AND (dish_name ILIKE %s OR restaurant_name ILIKE %s)
                ORDER BY dish_name
                LIMIT 10
            """, (pattern, pattern))
            rows = cur.fetchall()
            return [{"name": r["dish_name"], "restaurant_name": r["restaurant_name"]} for r in rows]


@router.get("/dishes/{dish_name}/restaurant/{restaurant_name}")
def get_dish_page(dish_name: str, restaurant_name: str, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT dish_name, restaurant_name,
                   COUNT(*) AS review_count,
                   ROUND(AVG(rating)::numeric, 1) AS avg_rating,
                   MIN(logged_at) AS first_logged,
                   (ARRAY_AGG(user_email ORDER BY logged_at ASC))[1] AS created_by
            FROM dish_reviews
            WHERE dish_name ILIKE %s AND restaurant_name ILIKE %s AND type = 'restaurant'
            GROUP BY dish_name, restaurant_name
        """, (dish_name, restaurant_name))
        stats = cur.fetchone()
        if not stats:
            raise HTTPException(status_code=404, detail="Dish not found")

        cur.execute("""
            SELECT id, user_email, rating, review, logged_at, meal_id FROM dish_reviews
            WHERE dish_name ILIKE %s AND restaurant_name ILIKE %s AND type = 'restaurant'
            ORDER BY logged_at DESC
        """, (dish_name, restaurant_name))
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
    owner_filter = """
        type = 'homemade' AND dish_name ILIKE %s
        AND COALESCE(recipe_owner_email, user_email) = %s
    """
    with with_cursor(db) as cur:
        cur.execute(f"""
            SELECT MIN(dish_name) AS dish_name,
                   COUNT(*) AS review_count,
                   ROUND(AVG(rating)::numeric, 1) AS avg_rating,
                   MIN(logged_at) AS first_logged
            FROM dish_reviews WHERE {owner_filter}
        """, (dish_name, owner))
        stats = cur.fetchone()
        if not stats or stats["review_count"] == 0:
            raise HTTPException(status_code=404, detail="Recipe not found")

        # The recipe text: prefer the owner's own latest version, else anyone's
        cur.execute(f"""
            SELECT id, recipe FROM dish_reviews
            WHERE {owner_filter} AND (COALESCE(recipe,'') <> '' OR EXISTS
            (SELECT 1 FROM recipe_ingredients ri WHERE ri.review_id = dish_reviews.id))
            ORDER BY (user_email = %s) DESC, logged_at DESC
            LIMIT 1
        """, (dish_name, owner, owner))
        recipe_row = cur.fetchone()
        ingredients = load_ingredients(cur, recipe_row["id"]) if recipe_row else []

        cur.execute(f"""
            SELECT id, user_email, rating, review, logged_at, meal_id
            FROM dish_reviews WHERE {owner_filter}
            ORDER BY logged_at DESC
        """, (dish_name, owner))
        reviews = cur.fetchall()

    return {
        "dish_name":        stats["dish_name"],
        "restaurant_name":  None,
        "review_count":     stats["review_count"],
        "avg_rating":       float(stats["avg_rating"]),
        "created_by":       username_from(owner),
        "created_by_email": owner,
        "first_logged":     stats["first_logged"],
        "recipe":           (recipe_row["recipe"] or "") if recipe_row else "",   # ←
        "ingredients":      ingredients,
        "reviews":          [serialise_review(r) for r in reviews],
    }
