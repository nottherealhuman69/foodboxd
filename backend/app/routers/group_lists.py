"""Shared group lists, invites and members."""

from fastapi import APIRouter, Depends, HTTPException

from app.core.db import get_db
from app.core.security import get_current_user
from app.schemas.lists import GroupInviteAction, GroupInviteBody, GroupListCreate, GroupListItemCreate, GroupListVisibility
from app.services.group_lists import group_membership, invite_friends, require_active_member, require_read_access
from app.services.lists import LIST_ITEM_STATS, list_item_stats_params
from app.utils import username_from, with_cursor

router = APIRouter()


@router.get("/group-lists")
def get_group_lists(email: str = Depends(get_current_user), db=Depends(get_db)):
    """Group lists the caller has actually joined."""
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT gl.id, gl.name, gl.owner_email, gl.is_public, gl.created_at, me.role AS my_role,
                   (SELECT COUNT(*) FROM group_list_members m
                     WHERE m.group_list_id = gl.id AND m.status = 'accepted') AS member_count,
                   (SELECT COUNT(*) FROM group_list_members m
                     WHERE m.group_list_id = gl.id AND m.status = 'pending')  AS pending_count,
                   (SELECT COUNT(*) FROM group_list_items i
                     WHERE i.group_list_id = gl.id) AS item_count
            FROM group_lists gl
            JOIN group_list_members me ON me.group_list_id = gl.id
            WHERE me.user_email = %s AND me.status = 'accepted'
            ORDER BY gl.created_at DESC
        """, (email,))
        rows = cur.fetchall()
    return [{**dict(r), "owner_username": username_from(r["owner_email"])} for r in rows]


@router.get("/group-lists/invites")
def get_group_invites(email: str = Depends(get_current_user), db=Depends(get_db)):
    """Pending invites for the caller — powers the Notifications tab."""
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT m.group_list_id, m.invited_by, m.invited_at,
                   gl.name, gl.owner_email,
                   (SELECT COUNT(*) FROM group_list_members mm
                     WHERE mm.group_list_id = gl.id AND mm.status = 'accepted') AS member_count
            FROM group_list_members m
            JOIN group_lists gl ON gl.id = m.group_list_id
            WHERE m.user_email = %s AND m.status = 'pending'
            ORDER BY m.invited_at DESC
        """, (email,))
        rows = cur.fetchall()
    return [{
        "group_list_id":   r["group_list_id"],
        "name":            r["name"],
        "invited_by":      r["invited_by"],
        "invited_by_username": username_from(r["invited_by"]) if r["invited_by"] else None,
        "owner_username":  username_from(r["owner_email"]),
        "member_count":    r["member_count"],
        "invited_at":      r["invited_at"],
    } for r in rows]


@router.post("/group-lists", status_code=201)
def create_group_list(body: GroupListCreate, email: str = Depends(get_current_user),
                      db=Depends(get_db)):
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="List name cannot be empty")
    with with_cursor(db) as cur:
        cur.execute(
            "INSERT INTO group_lists (name, owner_email, is_public) VALUES (%s, %s, %s) RETURNING *",
            (body.name.strip(), email, body.is_public)
        )
        gl = cur.fetchone()
        # The creator joins immediately — they never get an invite for their own list.
        cur.execute("""
            INSERT INTO group_list_members (group_list_id, user_email, role, status, responded_at)
            VALUES (%s, %s, 'owner', 'accepted', NOW())
        """, (gl["id"], email))
        result = invite_friends(cur, gl["id"], email, body.invite_emails)
        db.commit()
    return {
        **dict(gl),
        "owner_username": username_from(email),
        "my_role":        "owner",
        "member_count":   1,
        "pending_count":  len(result["invited"]),
        "item_count":     0,
        "skipped":        result["skipped"],
    }


@router.post("/group-lists/{list_id}/invite", status_code=201)
def invite_to_group_list(list_id: int, body: GroupInviteBody,
                         email: str = Depends(get_current_user), db=Depends(get_db)):
    """Any accepted member can pull in one of their own friends."""
    with with_cursor(db) as cur:
        require_active_member(cur, list_id, email)
        result = invite_friends(cur, list_id, email, body.emails)
        db.commit()
    return result


@router.patch("/group-lists/{list_id}/invite")
def respond_to_group_invite(list_id: int, body: GroupInviteAction,
                            email: str = Depends(get_current_user), db=Depends(get_db)):
    """
    Accept or decline. Declining only affects this member — the list stays alive
    for everyone who accepted, and anyone who never responds just stays pending.
    """
    if body.action not in ("accept", "decline"):
        raise HTTPException(status_code=400, detail="action must be 'accept' or 'decline'")
    with with_cursor(db) as cur:
        m = group_membership(cur, list_id, email)
        if not m or m["status"] != "pending":
            raise HTTPException(status_code=404, detail="Invite not found")
        new_status = "accepted" if body.action == "accept" else "declined"
        cur.execute("""
            UPDATE group_list_members SET status = %s, responded_at = NOW()
            WHERE group_list_id = %s AND user_email = %s
        """, (new_status, list_id, email))
        db.commit()
    return {"group_list_id": list_id, "status": new_status}


@router.patch("/group-lists/{list_id}/visibility")
def set_group_list_visibility(list_id: int, body: GroupListVisibility,
                              email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        require_active_member(cur, list_id, email)
        cur.execute("UPDATE group_lists SET is_public = %s WHERE id = %s RETURNING id, name, is_public",
                    (body.is_public, list_id))
        row = cur.fetchone()
        db.commit()
    return dict(row)


@router.get("/group-lists/{list_id}")
def get_group_list(list_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        me = require_read_access(cur, list_id, email)
        cur.execute("SELECT * FROM group_lists WHERE id = %s", (list_id,))
        gl = cur.fetchone()
        cur.execute("""
            SELECT user_email, role, status, invited_by, invited_at, responded_at
            FROM group_list_members
            WHERE group_list_id = %s AND status IN ('accepted', 'pending')
            ORDER BY CASE role WHEN 'owner' THEN 0 ELSE 1 END, invited_at ASC
        """, (list_id,))
        members = cur.fetchall()
    return {
        **dict(gl),
        "owner_username": username_from(gl["owner_email"]),
        "my_role": me["role"] if me else None,
        "members": [{
            "email":    m["user_email"],
            "username": username_from(m["user_email"]),
            "role":     m["role"],
            "status":   m["status"],
        } for m in members],
    }


@router.get("/group-lists/{list_id}/items")
def get_group_list_items(list_id: int, email: str = Depends(get_current_user),
                         db=Depends(get_db)):
    with with_cursor(db) as cur:
        require_read_access(cur, list_id, email)
        cur.execute(f"""
            SELECT i.*, s.avg_rating, s.review_count, s.my_rating
            FROM group_list_items i
            {LIST_ITEM_STATS}
            WHERE i.group_list_id = %s
            ORDER BY i.added_at ASC
        """, list_item_stats_params(email) + (list_id,))
        rows = cur.fetchall()
    return [{**dict(r), "added_by_username": username_from(r["added_by"])} for r in rows]


@router.post("/group-lists/{list_id}/items", status_code=201)
def add_group_list_item(list_id: int, body: GroupListItemCreate,
                        email: str = Depends(get_current_user), db=Depends(get_db)):
    if body.item_type not in ("dish", "restaurant", "recipe"):
        raise HTTPException(status_code=400,
                            detail="item_type must be 'dish', 'restaurant', or 'recipe'")
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="name cannot be empty")
    with with_cursor(db) as cur:
        require_active_member(cur, list_id, email)
        restaurant_name = body.restaurant_name.strip() if body.restaurant_name else None
        cur.execute("""
            SELECT gli.added_by FROM group_list_items gli
            WHERE group_list_id = %s AND item_type = %s AND name ILIKE %s
              AND COALESCE(restaurant_name, '') ILIKE COALESCE(%s, '')
        """, (list_id, body.item_type, body.name.strip(), restaurant_name))
        dupe = cur.fetchone()
        if dupe:
            raise HTTPException(
                status_code=409,
                detail=f"@{username_from(dupe['added_by'])} already added this to the list"
            )
        recipe_owner = (body.recipe_owner_email or email) if body.item_type == "recipe" else None
        cur.execute("""
            INSERT INTO group_list_items (group_list_id, added_by, item_type, name, restaurant_name, note, recipe_owner_email)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *
        """, (list_id, email, body.item_type, body.name.strip(), restaurant_name,
              body.note.strip() if body.note else None, recipe_owner))
        row = cur.fetchone()
        db.commit()
    return {**dict(row), "added_by_username": username_from(email)}


@router.delete("/group-lists/{list_id}/items/{item_id}", status_code=204)
def remove_group_list_item(list_id: int, item_id: int,
                           email: str = Depends(get_current_user), db=Depends(get_db)):
    """You can remove what you added; the owner can remove anything."""
    with with_cursor(db) as cur:
        me = require_active_member(cur, list_id, email)
        cur.execute("SELECT added_by FROM group_list_items WHERE id = %s AND group_list_id = %s",
                    (item_id, list_id))
        item = cur.fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        if item["added_by"] != email and me["role"] != "owner":
            raise HTTPException(status_code=403,
                                detail="Only the person who added this, or the list owner, can remove it")
        cur.execute("DELETE FROM group_list_items WHERE id = %s", (item_id,))
        db.commit()


@router.post("/group-lists/{list_id}/leave", status_code=204)
def leave_group_list(list_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        me = require_active_member(cur, list_id, email)
        if me["role"] == "owner":
            raise HTTPException(status_code=400,
                                detail="Owners can't leave — delete the list instead")
        cur.execute("""
            UPDATE group_list_members SET status = 'declined', responded_at = NOW()
            WHERE group_list_id = %s AND user_email = %s
        """, (list_id, email))
        db.commit()


@router.delete("/group-lists/{list_id}", status_code=204)
def delete_group_list(list_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM group_lists WHERE id = %s AND owner_email = %s",
                    (list_id, email))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Group list not found")
        cur.execute("DELETE FROM group_lists WHERE id = %s", (list_id,))
        db.commit()
