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
    }


@contextmanager
def with_cursor(db):
    """Open a cursor, yield it, close it — even on error."""
    cur = db.cursor()
    try:
        yield cur
    finally:
        cur.close()
