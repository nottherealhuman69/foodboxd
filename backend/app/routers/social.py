"""Follows and friend requests."""

from fastapi import APIRouter, Depends, HTTPException

from app.core.db import get_db
from app.core.security import get_current_user
from app.schemas.social import FriendActionBody, FriendRequestBody, FriendRequestOut
from app.utils import username_from, with_cursor

router = APIRouter()


@router.post("/friends/request", status_code=201)
def send_friend_request(body: FriendRequestBody, email: str = Depends(get_current_user), db=Depends(get_db)):
    """Follow a user. Public accounts are followed instantly (accepted);
    private accounts get a pending request the owner must approve."""
    if body.addressee_email == email:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    with with_cursor(db) as cur:
        cur.execute("SELECT is_private FROM users WHERE email = %s", (body.addressee_email,))
        target = cur.fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="User not found")
        # Only the caller's own follow direction matters (requester = me).
        cur.execute("""
            SELECT id, status FROM friendships
            WHERE requester_email = %s AND addressee_email = %s
        """, (email, body.addressee_email))
        existing = cur.fetchone()
        new_status = "pending" if target["is_private"] else "accepted"
        if existing and existing["status"] == "pending":
            raise HTTPException(status_code=409, detail="Request already pending")
        if existing and existing["status"] == "accepted":
            raise HTTPException(status_code=409, detail="Already following")
        if existing:  # previously declined — reopen following the current privacy rule
            cur.execute(
                "UPDATE friendships SET status = %s, updated_at = NOW() WHERE id = %s RETURNING *",
                (new_status, existing["id"])
            )
        else:
            cur.execute(
                "INSERT INTO friendships (requester_email, addressee_email, status) VALUES (%s, %s, %s) RETURNING *",
                (email, body.addressee_email, new_status)
            )
        row = cur.fetchone()
        db.commit()
    return row


@router.delete("/follow/{user_email}", status_code=204)
def unfollow(user_email: str, email: str = Depends(get_current_user), db=Depends(get_db)):
    """Stop following a user (removes my follow; leaves their follow of me intact)."""
    with with_cursor(db) as cur:
        cur.execute("""
            DELETE FROM friendships
            WHERE requester_email = %s AND addressee_email = %s
        """, (email, user_email))
        db.commit()


@router.get("/friends/requests/pending")
def get_pending_requests(email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT id, requester_email, created_at FROM friendships
            WHERE addressee_email = %s AND status = 'pending'
            ORDER BY created_at DESC
        """, (email,))
        return cur.fetchall()


@router.patch("/friends/requests/{request_id}", response_model=FriendRequestOut)
def respond_to_request(request_id: int, body: FriendActionBody, email: str = Depends(get_current_user), db=Depends(get_db)):
    if body.action not in ("accept", "decline"):
        raise HTTPException(status_code=400, detail="action must be 'accept' or 'decline'")
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM friendships WHERE id = %s AND addressee_email = %s", (request_id, email))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Request not found")
        new_status = "accepted" if body.action == "accept" else "declined"
        cur.execute(
            "UPDATE friendships SET status = %s, updated_at = NOW() WHERE id = %s RETURNING *",
            (new_status, request_id)
        )
        row = cur.fetchone()
        db.commit()
    return row


@router.get("/friends")
def get_friends(email: str = Depends(get_current_user), db=Depends(get_db)):
    """People the caller follows (used for the feed source and tag pickers)."""
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT f.addressee_email AS friend_email, COUNT(r.id) AS review_count
            FROM friendships f
            LEFT JOIN dish_reviews r ON r.user_email = f.addressee_email
            WHERE f.requester_email = %s AND f.status = 'accepted'
            GROUP BY f.addressee_email
        """, (email,))
        rows = cur.fetchall()
    return [{"email": r["friend_email"], "username": username_from(r["friend_email"]), "review_count": r["review_count"]} for r in rows]
