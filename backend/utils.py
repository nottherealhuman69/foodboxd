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
        "rating":          row.get("rating"),
        "review":          row.get("review") or "",
        "logged_at":       row.get("logged_at"),
        "meal_id":         row.get("meal_id"),
    }

def serialise_meal(meal: dict, dish_rows: list) -> dict:
    """A meal plus the dish_reviews rows that belong to it."""
    ratings = [d["rating"] for d in dish_rows]
    return {
        "id":              meal["id"],
        "kind":            "meal",
        "username":        username_from(meal.get("user_email", "")),
        "user_email":      meal.get("user_email", ""),
        "restaurant_name": meal["restaurant_name"],
        "title":           meal.get("title"),
        "rating":          meal["rating"],
        "review":          meal.get("review") or "",
        "logged_at":       meal.get("logged_at"),
        "dish_count":      len(dish_rows),
        "dish_avg":        round(sum(ratings) / len(ratings), 1) if ratings else None,
        "dishes": [
            {
                "id":        d["id"],
                "dish_name": d["dish_name"],
                "rating":    d["rating"],
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
