"""Recipe ingredient validation and storage."""

from fastapi import HTTPException


UNITS = ('g', 'kg', 'ml', 'l', 'tsp', 'tbsp', 'cup', 'pcs', 'pinch')


def clean_ingredients(items):
    out, seen = [], set()
    for i in items:
        name = i.name.strip()
        if not name:
            continue
        if name.lower() in seen:
            raise HTTPException(400, f"'{name}' is listed twice")
        if i.quantity is None or i.quantity <= 0:
            raise HTTPException(400, f"Enter an amount for '{name}'")
        if i.unit not in UNITS:
            raise HTTPException(400, f"Unknown unit '{i.unit}' for '{name}'")
        seen.add(name.lower())
        out.append((name, i.quantity, i.unit))
    if not out:
        raise HTTPException(400, "A homemade dish needs at least one ingredient")
    return out


def set_ingredients(cur, review_id, rows):
    cur.execute("DELETE FROM recipe_ingredients WHERE review_id = %s", (review_id,))
    for pos, (name, qty, unit) in enumerate(rows):
        cur.execute("""INSERT INTO recipe_ingredients (review_id, position, name, quantity, unit)
                       VALUES (%s, %s, %s, %s, %s)""", (review_id, pos, name, qty, unit))


def load_ingredients(cur, review_id):
    cur.execute("""SELECT name, quantity, unit FROM recipe_ingredients
                   WHERE review_id = %s ORDER BY position""", (review_id,))
    return [{"name": r["name"], "quantity": float(r["quantity"]), "unit": r["unit"]}
            for r in cur.fetchall()]
