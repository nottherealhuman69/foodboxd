"""Follow / friendship checks."""


def are_friends(cur, a: str, b: str) -> bool:
    cur.execute("""
        SELECT 1 FROM friendships
        WHERE status = 'accepted'
          AND ((requester_email = %s AND addressee_email = %s)
            OR (requester_email = %s AND addressee_email = %s))
    """, (a, b, b, a))
    return cur.fetchone() is not None


def is_following(cur, follower: str, followee: str) -> bool:
    """True if `follower` has an accepted follow of `followee`."""
    cur.execute("""
        SELECT 1 FROM friendships
        WHERE requester_email = %s AND addressee_email = %s AND status = 'accepted'
    """, (follower, followee))
    return cur.fetchone() is not None
