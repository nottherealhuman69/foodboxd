"""Meal loading helpers."""


def load_meal(cur, meal_id: int):
    cur.execute("SELECT * FROM meals WHERE id = %s", (meal_id,))
    meal = cur.fetchone()
    if not meal:
        return None, None
    cur.execute("""
        SELECT id, dish_name, rating, review
        FROM dish_reviews
        WHERE meal_id = %s
        ORDER BY id ASC
    """, (meal_id,))
    return meal, cur.fetchall()
