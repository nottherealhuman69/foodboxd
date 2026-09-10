from contextlib import contextmanager


def username_from(email: str) -> str:
    """'user@example.com' → 'user'"""
    return email.split("@")[0] if email else ""


def serialise_review(row: dict) -> dict:
    """Standard review shape returned by the feed, search, and dish/restaurant pages."""
    return {
        "id":              row["id"],
        "username":        username_from(row.get("user_email", "")),
        "user_email":      row.get("user_email", ""),
        "dish_name":       row.get("dish_name", ""),
        "type":            row.get("type", ""),
        "restaurant_name": row.get("restaurant_name"),
        "recipe":          row.get("recipe") or "",
        "recipe_owner_email": row.get("recipe_owner_email"),
        "recipe_owner":    username_from(row["recipe_owner_email"]) if row.get("recipe_owner_email") else None,
        "rating":          float(row["rating"]) if row.get("rating") is not None else None,
        "review":          row.get("review") or "",
        "logged_at":       row.get("logged_at"),
        "meal_id":         row.get("meal_id"),
    }

def serialise_meal(meal: dict, dish_rows: list) -> dict:
    """A meal plus the dish_reviews rows that belong to it."""
    ratings = [float(d["rating"]) for d in dish_rows if d.get("rating") is not None]
    return {
        "id":              meal["id"],
        "kind":            "meal",
        "username":        username_from(meal.get("user_email", "")),
        "user_email":      meal.get("user_email", ""),
        "restaurant_name": meal["restaurant_name"],
        "title":           meal.get("title"),
        "rating":          float(meal["rating"]) if meal.get("rating") is not None else None,
        "review":          meal.get("review") or "",
        "logged_at":       meal.get("logged_at"),
        "dish_count":      len(dish_rows),
        "dish_avg":        round(sum(ratings) / len(ratings), 1) if ratings else None,
        "dishes": [
            {
                "id":        d["id"],
                "dish_name": d["dish_name"],
                "rating":    float(d["rating"]) if d.get("rating") is not None else None,
                "review":    d.get("review") or "",
            }
            for d in dish_rows
        ],
    }

@contextmanager
def with_cursor(db):
    """Open a cursor, yield it, close it — even on error."""
    cur = db.cursor()
    try:
        yield cur
    finally:
        cur.close()
