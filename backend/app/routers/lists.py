"""Personal custom lists."""

from fastapi import APIRouter, Depends, HTTPException

from app.core.db import get_db
from app.core.security import get_current_user
from app.schemas.lists import ListCreate, ListItemCreate
from app.services.lists import LIST_ITEM_STATS, list_item_stats_params
from app.utils import with_cursor

router = APIRouter()


@router.get("/lists")
def get_lists(email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT cl.id, cl.name, cl.is_public, cl.created_at,
                   COUNT(li.id) AS item_count
            FROM custom_lists cl
            LEFT JOIN list_items li ON li.list_id = cl.id
            WHERE cl.user_email = %s
            GROUP BY cl.id
            ORDER BY cl.created_at DESC
        """, (email,))
        return cur.fetchall()


@router.post("/lists", status_code=201)
def create_list(body: ListCreate, email: str = Depends(get_current_user), db=Depends(get_db)):
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="List name cannot be empty")
    with with_cursor(db) as cur:
        cur.execute(
            "INSERT INTO custom_lists (user_email, name, is_public) VALUES (%s, %s, %s) RETURNING *",
            (email, body.name.strip(), body.is_public)
        )
        row = cur.fetchone()
        db.commit()
    return {**dict(row), "item_count": 0}


@router.delete("/lists/{list_id}", status_code=204)
def delete_list(list_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM custom_lists WHERE id = %s AND user_email = %s", (list_id, email))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="List not found")
        cur.execute("DELETE FROM custom_lists WHERE id = %s", (list_id,))
        db.commit()


@router.post("/lists/{list_id}/items", status_code=201)
def add_list_item(list_id: int, body: ListItemCreate, email: str = Depends(get_current_user), db=Depends(get_db)):
    if body.item_type not in ("dish", "restaurant", "recipe"):
        raise HTTPException(status_code=400, detail="item_type must be 'dish', 'restaurant', or 'recipe'")
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="name cannot be empty")
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM custom_lists WHERE id = %s AND user_email = %s", (list_id, email))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="List not found")

        restaurant_name = body.restaurant_name.strip() if body.restaurant_name else None
        cur.execute("""
            SELECT id FROM list_items
            WHERE list_id = %s AND item_type = %s
              AND name ILIKE %s
              AND COALESCE(restaurant_name, '') ILIKE COALESCE(%s, '')
        """, (list_id, body.item_type, body.name.strip(), restaurant_name))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="This item is already in the list")

        recipe_owner = (body.recipe_owner_email or email) if body.item_type == "recipe" else None
        cur.execute(
            """INSERT INTO list_items (list_id, item_type, name, restaurant_name, note, recipe_owner_email)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING *""",
            (list_id, body.item_type, body.name.strip(), restaurant_name,
             body.note.strip() if body.note else None, recipe_owner)
        )
        row = cur.fetchone()
        db.commit()
    return row


@router.delete("/lists/{list_id}/items/{item_id}", status_code=204)
def remove_list_item(list_id: int, item_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM custom_lists WHERE id = %s AND user_email = %s", (list_id, email))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="List not found")
        cur.execute("SELECT id FROM list_items WHERE id = %s AND list_id = %s", (item_id, list_id))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Item not found")
        cur.execute("DELETE FROM list_items WHERE id = %s", (item_id,))
        db.commit()


@router.get("/lists/{list_id}/items")
def get_list_items(list_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute(
            "SELECT id FROM custom_lists WHERE id = %s AND (user_email = %s OR is_public = TRUE)",
            (list_id, email)
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="List not found")
        cur.execute(f"""
            SELECT i.*, s.avg_rating, s.review_count, s.my_rating
            FROM list_items i
            {LIST_ITEM_STATS}
            WHERE i.list_id = %s
            ORDER BY i.added_at ASC
        """, list_item_stats_params(email) + (list_id,))
        return cur.fetchall()
