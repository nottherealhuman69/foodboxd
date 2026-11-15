"""Group list membership, access checks and invites."""

from fastapi import HTTPException

from app.services.social import are_friends


def group_membership(cur, group_list_id: int, email: str):
    """Returns the member row (role, status) or None."""
    cur.execute("""
        SELECT role, status FROM group_list_members
        WHERE group_list_id = %s AND user_email = %s
    """, (group_list_id, email))
    return cur.fetchone()


def require_active_member(cur, group_list_id: int, email: str):
    """404s if the list doesn't exist or the caller isn't an accepted member."""
    m = group_membership(cur, group_list_id, email)
    if not m or m["status"] != "accepted":
        raise HTTPException(status_code=404, detail="Group list not found")
    return m


def require_read_access(cur, group_list_id: int, email: str):
    """
    Accepted members always get in. Everyone else gets in only if the list
    is public. Returns the member row, or None for a public-list outsider.
    """
    m = group_membership(cur, group_list_id, email)
    if m and m["status"] == "accepted":
        return m
    cur.execute("SELECT is_public FROM group_lists WHERE id = %s", (group_list_id,))
    gl = cur.fetchone()
    if not gl or not gl["is_public"]:
        raise HTTPException(status_code=404, detail="Group list not found")
    return None


def invite_friends(cur, group_list_id: int, inviter: str, emails: list) -> dict:
    """
    Inserts pending invites. Silently skips the inviter, non-friends, and
    anyone already invited or already a member. Re-invites people who declined.
    Returns {'invited': [...], 'skipped': [...]}.
    """
    invited, skipped = [], []
    for target in emails:
        if target == inviter:
            continue
        if not are_friends(cur, inviter, target):
            skipped.append(target)
            continue
        existing = group_membership(cur, group_list_id, target)
        if existing and existing["status"] in ("pending", "accepted"):
            continue
        if existing:  # previously declined — reopen the invite
            cur.execute("""
                UPDATE group_list_members
                SET status = 'pending', invited_by = %s, invited_at = NOW(), responded_at = NULL
                WHERE group_list_id = %s AND user_email = %s
            """, (inviter, group_list_id, target))
        else:
            cur.execute("""
                INSERT INTO group_list_members (group_list_id, user_email, role, status, invited_by)
                VALUES (%s, %s, 'member', 'pending', %s)
            """, (group_list_id, target, inviter))
        invited.append(target)
    return {"invited": invited, "skipped": skipped}
