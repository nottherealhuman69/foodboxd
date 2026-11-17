"""Actions shared by reviews and meals: reposts and comment likes."""

from fastapi import APIRouter, Depends, HTTPException

from app.core.db import get_db
from app.core.security import get_current_user
from app.services.posts import find_my_fork, repost_state
from app.services.privacy import require_visible_meal, require_visible_review
from app.utils import with_cursor

router = APIRouter()


@router.post("/posts/{post_type}/{post_id}/repost")
def toggle_repost(post_type: str, post_id: int,
                  email: str = Depends(get_current_user), db=Depends(get_db)):
    """Repost (or undo a repost of) a post you're tagged in. You can't repost a
    post you've already forked: the fork is your version of it."""
    if post_type not in ("review", "meal"):
        raise HTTPException(status_code=400, detail="post_type must be 'review' or 'meal'")
    with with_cursor(db) as cur:
        if post_type == "review":
            cur.execute("SELECT id FROM dish_reviews WHERE id = %s AND meal_id IS NULL", (post_id,))
        else:
            cur.execute("SELECT id FROM meals WHERE id = %s", (post_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Post not found")

        state = repost_state(cur, post_type, post_id, email)
        if not state["is_tagged"]:
            raise HTTPException(status_code=403, detail="You can only repost posts you're tagged in")

        if state["user_reposted"]:
            cur.execute("""DELETE FROM post_reposts
                           WHERE post_type = %s AND post_id = %s AND reposter_email = %s""",
                        (post_type, post_id, email))
            reposted = False
        else:
            if find_my_fork(cur, post_type, post_id, email):
                raise HTTPException(status_code=409, detail="You've already forked this post")
            cur.execute("""INSERT INTO post_reposts (post_type, post_id, reposter_email)
                           VALUES (%s, %s, %s) ON CONFLICT DO NOTHING""",
                        (post_type, post_id, email))
            reposted = True
        db.commit()
    return {"reposted": reposted}


@router.post("/comments/{comment_type}/{comment_id}/like")
def toggle_comment_like(comment_type: str, comment_id: int,
                        email: str = Depends(get_current_user), db=Depends(get_db)):
    if comment_type not in ("review", "meal"):
        raise HTTPException(status_code=400, detail="comment_type must be 'review' or 'meal'")
    # Table names come from a fixed whitelist, so interpolation here is safe.
    comment_table = "review_comments" if comment_type == "review" else "meal_comments"
    like_table    = "review_comment_likes" if comment_type == "review" else "meal_comment_likes"
    post_column   = "review_id" if comment_type == "review" else "meal_id"
    with with_cursor(db) as cur:
        cur.execute(f"SELECT {post_column} AS post_id FROM {comment_table} WHERE id = %s", (comment_id,))
        comment = cur.fetchone()
        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")
        try:
            if comment_type == "review":
                require_visible_review(cur, comment["post_id"], email)
            else:
                require_visible_meal(cur, comment["post_id"], email)
        except HTTPException:
            raise HTTPException(status_code=404, detail="Comment not found")
        cur.execute(f"SELECT id FROM {like_table} WHERE comment_id = %s AND user_email = %s", (comment_id, email))
        if cur.fetchone():
            cur.execute(f"DELETE FROM {like_table} WHERE comment_id = %s AND user_email = %s", (comment_id, email))
            liked = False
        else:
            cur.execute(f"INSERT INTO {like_table} (comment_id, user_email) VALUES (%s, %s)", (comment_id, email))
            liked = True
        cur.execute(f"SELECT COUNT(*) AS count FROM {like_table} WHERE comment_id = %s", (comment_id,))
        count = cur.fetchone()["count"]
        db.commit()
    return {"liked": liked, "like_count": int(count)}
