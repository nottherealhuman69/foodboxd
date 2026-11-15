"""The personal try-list."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from app.core.db import get_db
from app.core.security import get_current_user
from app.schemas.lists import TrylistAdd
from app.utils import with_cursor

router = APIRouter()


@router.get("/trylist/check")
def check_trylist(item_type: str, restaurant_name: str, dish_name: Optional[str] = None,
                  email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT id FROM trylists
            WHERE user_email = %s AND item_type = %s
              AND (dish_name IS NOT DISTINCT FROM %s)
              AND restaurant_name ILIKE %s
        """, (email, item_type, dish_name, restaurant_name))
        row = cur.fetchone()
    return {"in_trylist": row is not None, "id": row["id"] if row else None}


@router.get("/trylist")
def get_trylist(email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT id, item_type, dish_name, restaurant_name, added_at
            FROM trylists WHERE user_email = %s ORDER BY added_at DESC
        """, (email,))
        return cur.fetchall()


@router.post("/trylist", status_code=201)
def add_to_trylist(body: TrylistAdd, email: str = Depends(get_current_user), db=Depends(get_db)):
    if body.item_type not in ("dish", "restaurant"):
        raise HTTPException(status_code=400, detail="item_type must be 'dish' or 'restaurant'")
    if body.item_type == "dish" and (not body.dish_name or not body.restaurant_name):
        raise HTTPException(status_code=400, detail="dish_name and restaurant_name required for dish")
    if body.item_type == "restaurant" and not body.restaurant_name:
        raise HTTPException(status_code=400, detail="restaurant_name required for restaurant")
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT id FROM trylists
            WHERE user_email = %s AND item_type = %s
              AND (dish_name IS NOT DISTINCT FROM %s) AND (restaurant_name ILIKE %s)
        """, (email, body.item_type, body.dish_name, body.restaurant_name))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="Already in trylist")
        cur.execute(
            "INSERT INTO trylists (user_email, item_type, dish_name, restaurant_name) VALUES (%s,%s,%s,%s) RETURNING *",
            (email, body.item_type, body.dish_name, body.restaurant_name)
        )
        row = cur.fetchone()
        db.commit()
    return row


@router.delete("/trylist/{item_id}", status_code=204)
def remove_from_trylist(item_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM trylists WHERE id = %s AND user_email = %s", (item_id, email))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Item not found")
        cur.execute("DELETE FROM trylists WHERE id = %s", (item_id,))
        db.commit()
