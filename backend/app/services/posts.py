"""Shared post logic: companion tags, reposts, forks and feed item loaders."""

from fastapi import HTTPException

from app.services.social import is_following
from app.utils import serialise_meal, serialise_review, username_from


def post_tags(cur, post_type: str, post_id: int) -> list:
    """Companion tags on a post, as [{email, username}] in tag order."""
    cur.execute("""
        SELECT tagged_email FROM post_tags
        WHERE post_type = %s AND post_id = %s
        ORDER BY id ASC
    """, (post_type, post_id))
    return [{"email": r["tagged_email"], "username": username_from(r["tagged_email"])}
            for r in cur.fetchall()]


def set_post_tags(cur, post_type: str, post_id: int, author: str, emails: list) -> None:
    """Sync a post's companion tags without re-notifying existing tags."""
    wanted, seen = [], set()
    for target in emails or []:
        target = (target or "").strip().lower()
        if not target or target == author or target in seen:
            continue
        if not is_following(cur, author, target):
            continue
        seen.add(target)
        wanted.append(target)

    cur.execute("SELECT tagged_email FROM post_tags WHERE post_type = %s AND post_id = %s",
                (post_type, post_id))
    existing = {r["tagged_email"] for r in cur.fetchall()}

    removed = list(existing - seen)
    if removed:
        cur.execute("""DELETE FROM post_tags
                       WHERE post_type = %s AND post_id = %s AND tagged_email = ANY(%s)""",
                    (post_type, post_id, removed))
        cur.execute("""DELETE FROM post_reposts
                       WHERE post_type = %s AND post_id = %s AND reposter_email = ANY(%s)""",
                    (post_type, post_id, removed))

    for target in wanted:
        if target not in existing:
            cur.execute("""INSERT INTO post_tags (post_type, post_id, tagged_email)
                           VALUES (%s, %s, %s) ON CONFLICT DO NOTHING""",
                        (post_type, post_id, target))


def delete_post_extras(cur, post_type: str, post_id: int) -> None:
    cur.execute("DELETE FROM post_tags    WHERE post_type = %s AND post_id = %s", (post_type, post_id))
    cur.execute("DELETE FROM post_reposts WHERE post_type = %s AND post_id = %s", (post_type, post_id))


def repost_state(cur, post_type: str, post_id: int, email: str) -> dict:
    cur.execute("""
        SELECT
          EXISTS (SELECT 1 FROM post_tags
                  WHERE post_type = %s AND post_id = %s AND tagged_email = %s)   AS is_tagged,
          EXISTS (SELECT 1 FROM post_reposts
                  WHERE post_type = %s AND post_id = %s AND reposter_email = %s) AS user_reposted
    """, (post_type, post_id, email) * 2)
    row = cur.fetchone()
    return {"is_tagged": bool(row["is_tagged"]), "user_reposted": bool(row["user_reposted"])}


def fork_source(cur, kind: str, forked_from_id):
    """Describe the post a fork came from, or None."""
    if not forked_from_id:
        return None
    if kind == "review":
        cur.execute("SELECT id, user_email, dish_name FROM dish_reviews WHERE id = %s",
                    (forked_from_id,))
        row = cur.fetchone()
        title = row["dish_name"] if row else None
    else:
        cur.execute("SELECT id, user_email, title, restaurant_name FROM meals WHERE id = %s",
                    (forked_from_id,))
        row = cur.fetchone()
        title = (row["title"] or f"meal at {row['restaurant_name']}") if row else None
    if not row:
        return None
    return {"kind": kind, "id": row["id"], "user_email": row["user_email"],
            "username": username_from(row["user_email"]), "title": title}


def check_fork_source(cur, kind: str, fork_id, email: str):
    """You can only fork a post you're tagged in, once, and not if you've reposted it."""
    if fork_id is None:
        return None
    if kind == "review":
        cur.execute("SELECT id FROM dish_reviews WHERE id = %s AND meal_id IS NULL", (fork_id,))
    else:
        cur.execute("SELECT id FROM meals WHERE id = %s", (fork_id,))
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="Original post not found")

    state = repost_state(cur, kind, fork_id, email)
    if not state["is_tagged"]:
        raise HTTPException(status_code=403, detail="You can only fork posts you're tagged in")
    if find_my_fork(cur, kind, fork_id, email):
        raise HTTPException(status_code=409, detail="You've already forked this post")
    if state["user_reposted"]:
        raise HTTPException(status_code=409, detail="You've reposted this post. Undo the repost to fork it instead")
    return fork_id


def find_my_fork(cur, kind: str, post_id: int, email: str):
    """The caller's fork of this post, if they've made one."""
    table = "dish_reviews" if kind == "review" else "meals"
    cur.execute(
        f"SELECT id FROM {table} WHERE forked_from_id = %s AND user_email = %s ORDER BY id LIMIT 1",
        (post_id, email),
    )
    row = cur.fetchone()
    return {"kind": kind, "id": row["id"]} if row else None


def feed_review(cur, review_id: int, viewer: str):
    cur.execute("""
        SELECT r.*,
               COUNT(DISTINCT l.id) AS like_count,
               COUNT(DISTINCT c.id) AS comment_count,
               COALESCE(BOOL_OR(l.user_email = %s), FALSE) AS user_liked
        FROM dish_reviews r
        LEFT JOIN review_likes l    ON l.review_id = r.id
        LEFT JOIN review_comments c ON c.review_id = r.id
        WHERE r.id = %s AND r.meal_id IS NULL
        GROUP BY r.id
    """, (viewer, review_id))
    r = cur.fetchone()
    if not r:
        return None
    return {**serialise_review(r), "kind": "review",
            "like_count": int(r["like_count"]), "comment_count": int(r["comment_count"]),
            "user_liked": bool(r["user_liked"]), "tagged": post_tags(cur, "review", r["id"]),
            "forked_from": fork_source(cur, "review", r["forked_from_id"])}


def feed_meal(cur, meal_id: int, viewer: str):
    cur.execute("""
        SELECT m.*,
               COUNT(DISTINCT l.id) AS like_count,
               COUNT(DISTINCT c.id) AS comment_count,
               COALESCE(BOOL_OR(l.user_email = %s), FALSE) AS user_liked
        FROM meals m
        LEFT JOIN meal_likes    l ON l.meal_id = m.id
        LEFT JOIN meal_comments c ON c.meal_id = m.id
        WHERE m.id = %s
        GROUP BY m.id
    """, (viewer, meal_id))
    m = cur.fetchone()
    if not m:
        return None
    cur.execute("SELECT id, dish_name, rating, review FROM dish_reviews WHERE meal_id = %s ORDER BY id ASC",
                (meal_id,))
    return {**serialise_meal(m, cur.fetchall()),
            "like_count": int(m["like_count"]), "comment_count": int(m["comment_count"]),
            "user_liked": bool(m["user_liked"]), "tagged": post_tags(cur, "meal", m["id"]),
            "forked_from": fork_source(cur, "meal", m["forked_from_id"])}


def reposts_by(cur, reposter_emails: list, viewer: str, post_type=None, limit: int = 50) -> list:
    if not reposter_emails:
        return []
    sql = "SELECT post_type, post_id, reposter_email, created_at FROM post_reposts WHERE reposter_email = ANY(%s)"
    params = [list(reposter_emails)]
    if post_type:
        sql += " AND post_type = %s"
        params.append(post_type)
    sql += " ORDER BY created_at DESC LIMIT %s"
    params.append(limit)
    cur.execute(sql, params)

    out = []
    for rp in cur.fetchall():
        loader = feed_review if rp["post_type"] == "review" else feed_meal
        item = loader(cur, rp["post_id"], viewer)
        if item:
            out.append({**item,
                        "reposted_by": {"email": rp["reposter_email"],
                                        "username": username_from(rp["reposter_email"])},
                        "reposted_at": rp["created_at"]})
    return out


def sort_at(item):
    return item.get("reposted_at") or item["logged_at"]
