from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import bcrypt
import psycopg2
from psycopg2.extras import RealDictCursor
import jwt
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from utils import with_cursor, serialise_review, serialise_meal, username_from
from typing import Optional


load_dotenv(override=True)

app = FastAPI(title="Dishlog API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security  = HTTPBearer()
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM  = "HS256"
DB_URL     = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/authdb")


# ── DB connection ─────────────────────────────────────────────────────────────

def get_db():
    conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()


# ── Table setup ───────────────────────────────────────────────────────────────

def create_tables():
    conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
    with with_cursor(conn) as cur:
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS group_lists (
                id          SERIAL PRIMARY KEY,
                name        VARCHAR(255) NOT NULL,
                owner_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                created_at  TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("""
            ALTER TABLE group_lists
            ADD COLUMN IF NOT EXISTS is_public BOOLEAN NOT NULL DEFAULT FALSE
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS group_list_members (
                id            SERIAL PRIMARY KEY,
                group_list_id INTEGER NOT NULL REFERENCES group_lists(id) ON DELETE CASCADE,
                user_email    VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                role          VARCHAR(20) NOT NULL DEFAULT 'member'
                              CHECK (role IN ('owner', 'member')),
                status        VARCHAR(20) NOT NULL DEFAULT 'pending'
                              CHECK (status IN ('pending', 'accepted', 'declined')),
                invited_by    VARCHAR(255),
                invited_at    TIMESTAMP DEFAULT NOW(),
                responded_at  TIMESTAMP,
                UNIQUE (group_list_id, user_email)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS group_list_items (
                id              SERIAL PRIMARY KEY,
                group_list_id   INTEGER NOT NULL REFERENCES group_lists(id) ON DELETE CASCADE,
                added_by        VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                item_type       VARCHAR(20) NOT NULL
                                CHECK (item_type IN ('dish', 'restaurant', 'recipe')),
                name            VARCHAR(255) NOT NULL,
                restaurant_name VARCHAR(255),
                note            TEXT,
                added_at        TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS group_list_items_unique_idx
            ON group_list_items (group_list_id, item_type, LOWER(name),
                                 COALESCE(LOWER(restaurant_name), ''))
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS group_list_members_user_idx
            ON group_list_members (user_email, status)
        """)
 
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                hashed_password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS meals (
                id              SERIAL PRIMARY KEY,
                user_email      VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                restaurant_name VARCHAR(255) NOT NULL,
                title           VARCHAR(255),
                rating          INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                review          TEXT,
                logged_at       TIMESTAMP DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS meal_likes (
                id         SERIAL PRIMARY KEY,
                meal_id    INTEGER NOT NULL REFERENCES meals(id) ON DELETE CASCADE,
                user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE (meal_id, user_email)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS meal_comments (
                id         SERIAL PRIMARY KEY,
                meal_id    INTEGER NOT NULL REFERENCES meals(id) ON DELETE CASCADE,
                user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                content    TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        cur.execute("""
            ALTER TABLE dish_reviews
            ADD COLUMN IF NOT EXISTS meal_id INTEGER REFERENCES meals(id) ON DELETE CASCADE
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS dish_reviews_meal_idx ON dish_reviews (meal_id)
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS dish_reviews (
                id SERIAL PRIMARY KEY,
                user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                dish_name VARCHAR(255) NOT NULL,
                type VARCHAR(20) NOT NULL CHECK (type IN ('restaurant', 'homemade')),
                restaurant_name VARCHAR(255),
                recipe TEXT,
                rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                review TEXT,
                logged_at TIMESTAMP DEFAULT NOW()
            )
        """)
        # Recipe ownership: NULL = original/your own recipe, else the tagged author's email.
        cur.execute("""
            ALTER TABLE dish_reviews
            ADD COLUMN IF NOT EXISTS recipe_owner_email VARCHAR(255)
                REFERENCES users(email) ON DELETE SET NULL
        """)
        # Half-star ratings: widen INTEGER → NUMERIC(2,1) and allow 0.5 as the floor.
        cur.execute("ALTER TABLE dish_reviews DROP CONSTRAINT IF EXISTS dish_reviews_rating_check")
        cur.execute("ALTER TABLE dish_reviews ALTER COLUMN rating TYPE NUMERIC(2,1)")
        cur.execute("ALTER TABLE dish_reviews ADD CONSTRAINT dish_reviews_rating_check CHECK (rating >= 0.5 AND rating <= 5)")
        cur.execute("ALTER TABLE meals DROP CONSTRAINT IF EXISTS meals_rating_check")
        cur.execute("ALTER TABLE meals ALTER COLUMN rating TYPE NUMERIC(2,1)")
        cur.execute("ALTER TABLE meals ADD CONSTRAINT meals_rating_check CHECK (rating >= 0.5 AND rating <= 5)")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS friendships (
                id SERIAL PRIMARY KEY,
                requester_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                addressee_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'declined')),
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                UNIQUE (requester_email, addressee_email)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS trylists (
                id               SERIAL PRIMARY KEY,
                user_email       VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                item_type        VARCHAR(20)  NOT NULL CHECK (item_type IN ('dish', 'restaurant')),
                dish_name        VARCHAR(255),
                restaurant_name  VARCHAR(255),
                added_at         TIMESTAMP DEFAULT NOW(),
                UNIQUE (user_email, item_type, dish_name, restaurant_name)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS review_likes (
                id SERIAL PRIMARY KEY,
                review_id INTEGER NOT NULL REFERENCES dish_reviews(id) ON DELETE CASCADE,
                user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE (review_id, user_email)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS review_comments (
                id SERIAL PRIMARY KEY,
                review_id INTEGER NOT NULL REFERENCES dish_reviews(id) ON DELETE CASCADE,
                user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS custom_lists (
                id         SERIAL PRIMARY KEY,
                user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                name       VARCHAR(255) NOT NULL,
                is_public  BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("""
            ALTER TABLE custom_lists
            ADD COLUMN IF NOT EXISTS is_public BOOLEAN NOT NULL DEFAULT TRUE
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS list_items (
                id              SERIAL PRIMARY KEY,
                list_id         INTEGER NOT NULL REFERENCES custom_lists(id) ON DELETE CASCADE,
                item_type       VARCHAR(20) NOT NULL CHECK (item_type IN ('dish', 'restaurant', 'recipe')),
                name            VARCHAR(255) NOT NULL,
                restaurant_name VARCHAR(255),
                note            TEXT,
                added_at        TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("""
            DELETE FROM list_items a
            USING list_items b
            WHERE a.id > b.id
            AND a.list_id = b.list_id
            AND a.item_type = b.item_type
            AND LOWER(a.name) = LOWER(b.name)
            AND COALESCE(LOWER(a.restaurant_name), '') = COALESCE(LOWER(b.restaurant_name), '')
        """)
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS list_items_unique_idx
            ON list_items (list_id, item_type, name, COALESCE(restaurant_name, ''))
        """)

        # ── Public/private accounts ──────────────────────────────────────────
        # FALSE = public (anyone can follow instantly); TRUE = private (follow
        # requests must be approved).
        cur.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS is_private BOOLEAN NOT NULL DEFAULT FALSE
        """)

        # ── Companion tags ("went with") ─────────────────────────────────────
        # Display-only: a tag never shows in the tagged user's own diary/feed,
        # only on the post owner's post.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS post_tags (
                id           SERIAL PRIMARY KEY,
                post_type    VARCHAR(10) NOT NULL CHECK (post_type IN ('review', 'meal')),
                post_id      INTEGER NOT NULL,
                tagged_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                created_at   TIMESTAMP DEFAULT NOW(),
                UNIQUE (post_type, post_id, tagged_email)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS post_reposts (
                id             SERIAL PRIMARY KEY,
                post_type      VARCHAR(10) NOT NULL CHECK (post_type IN ('review', 'meal')),
                post_id        INTEGER NOT NULL,
                reposter_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                created_at     TIMESTAMP DEFAULT NOW(),
                UNIQUE (post_type, post_id, reposter_email)
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS post_reposts_reposter_idx
            ON post_reposts (reposter_email, created_at DESC)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS post_tags_tagged_idx
            ON post_tags (tagged_email, created_at DESC)
        """)

        # ── Threaded comments (full nesting via self-referential parent_id) ──
        cur.execute("""
            ALTER TABLE review_comments
            ADD COLUMN IF NOT EXISTS parent_id INTEGER
                REFERENCES review_comments(id) ON DELETE CASCADE
        """)
        cur.execute("""
            ALTER TABLE meal_comments
            ADD COLUMN IF NOT EXISTS parent_id INTEGER
                REFERENCES meal_comments(id) ON DELETE CASCADE
        """)

        # ── Comment likes (separate tables so FK cascade cleans them up) ─────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS review_comment_likes (
                id         SERIAL PRIMARY KEY,
                comment_id INTEGER NOT NULL REFERENCES review_comments(id) ON DELETE CASCADE,
                user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE (comment_id, user_email)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS meal_comment_likes (
                id         SERIAL PRIMARY KEY,
                comment_id INTEGER NOT NULL REFERENCES meal_comments(id) ON DELETE CASCADE,
                user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE (comment_id, user_email)
            )
        """)

        # ── One-time backfill: preserve existing mutual friendships ──────────
        # Pre-follow-model, a single accepted friendship row meant a *mutual*
        # relationship. Moving to a directional follow graph, we backfill the
        # reverse row once so existing friends keep seeing each other's posts.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_flags (
                flag       VARCHAR(100) PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("SELECT 1 FROM schema_flags WHERE flag = 'friendship_backfill_v1'")
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO friendships (requester_email, addressee_email, status)
                SELECT f.addressee_email, f.requester_email, 'accepted'
                FROM friendships f
                WHERE f.status = 'accepted'
                  AND NOT EXISTS (
                      SELECT 1 FROM friendships r
                      WHERE r.requester_email = f.addressee_email
                        AND r.addressee_email = f.requester_email
                  )
                ON CONFLICT (requester_email, addressee_email) DO NOTHING
            """)
            cur.execute("INSERT INTO schema_flags (flag) VALUES ('friendship_backfill_v1')")

        # ── One-time: existing accounts become private ───────────────────────
        # Preserves the old mutual-friendship behaviour — their existing
        # (backfilled) mutual follows keep working, and any *new* follower now
        # needs approval, just like the old friend-request flow. New signups
        # still default to public (column default) and can switch in Settings.
        cur.execute("SELECT 1 FROM schema_flags WHERE flag = 'users_private_v1'")
        if not cur.fetchone():
            cur.execute("UPDATE users SET is_private = TRUE")
            cur.execute("INSERT INTO schema_flags (flag) VALUES ('users_private_v1')")

        conn.commit()
    conn.close()

create_tables()


# ── Pydantic models ───────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ReviewCreate(BaseModel):
    dish_name: str
    type: str
    restaurant_name: Optional[str] = None
    recipe: Optional[str] = None
    recipe_owner_email: Optional[str] = None
    rating: float
    review: Optional[str] = None
    tagged_emails: List[EmailStr] = []

class ReviewUpdate(BaseModel):
    dish_name: str
    type: str
    restaurant_name: Optional[str] = None
    recipe: Optional[str] = None
    recipe_owner_email: Optional[str] = None
    rating: float
    review: Optional[str] = None
    tagged_emails: List[EmailStr] = []

class MealDishIn(BaseModel):
    id: Optional[int] = None
    dish_name: str
    rating: float
    review: Optional[str] = None

class MealCreate(BaseModel):
    restaurant_name: str
    title: Optional[str] = None
    rating: float
    review: Optional[str] = None
    dishes: List[MealDishIn]
    tagged_emails: List[EmailStr] = []

class ReviewOut(BaseModel):
    id: int
    dish_name: str
    type: str
    restaurant_name: Optional[str]
    recipe: Optional[str]
    recipe_owner_email: Optional[str] = None
    rating: float
    review: Optional[str]
    logged_at: datetime
    like_count: int = 0
    comment_count: int = 0
    tagged: List[dict] = []
    reposted_by: Optional[dict] = None
    reposted_at: Optional[datetime] = None

class FriendRequestBody(BaseModel):
    addressee_email: EmailStr

class FriendActionBody(BaseModel):
    action: str

class FriendRequestOut(BaseModel):
    id: int
    requester_email: str
    addressee_email: str
    status: str
    created_at: datetime

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class TrylistAdd(BaseModel):
    item_type: str
    dish_name: Optional[str] = None
    restaurant_name: Optional[str] = None

class CommentCreate(BaseModel):
    content: str
    parent_id: Optional[int] = None

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class PrivacyUpdate(BaseModel):
    is_private: bool

class ListCreate(BaseModel):
    name: str
    is_public: bool = True

class ListItemCreate(BaseModel):
    item_type: str
    name: str
    restaurant_name: Optional[str] = None
    note: Optional[str] = None


class GroupListCreate(BaseModel):
    name: str
    invite_emails: List[EmailStr] = []
    is_public: bool = False

 
class GroupInviteBody(BaseModel):
    emails: List[EmailStr]
 
class GroupInviteAction(BaseModel):
    action: str  # 'accept' | 'decline'
 
class GroupListItemCreate(BaseModel):
    item_type: str
    name: str
    restaurant_name: Optional[str] = None
    note: Optional[str] = None

class GroupListVisibility(BaseModel):
    is_public: bool
# ── Auth helpers ──────────────────────────────────────────────────────────────

def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def create_token(email: str) -> str:
    payload = {"sub": email, "exp": datetime.utcnow() + timedelta(hours=24)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def valid_rating(r: float) -> bool:
    """Ratings run 0.5–5 in half-star steps."""
    return r is not None and 0.5 <= r <= 5 and (r * 2) == int(r * 2)

def create_reset_token(email: str) -> str:
    payload = {"sub": email, "purpose": "reset",
               "exp": datetime.utcnow() + timedelta(hours=1)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def send_reset_email(to_email: str, reset_link: str) -> None:
    """Send the password-reset link over Gmail SMTP. Falls back to logging the
    link if SMTP isn't configured or the send fails, so the flow never hard-crashes."""
    import smtplib
    from email.message import EmailMessage

    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))

    if not smtp_user or not smtp_pass:
        print(f"[reset] SMTP not configured — reset link for {to_email}: {reset_link}")
        return

    msg = EmailMessage()
    msg["Subject"] = "Reset your Dishlog password"
    msg["From"]    = smtp_user
    msg["To"]      = to_email
    msg.set_content(
        f"We received a request to reset your Dishlog password.\n\n"
        f"Reset it here (link expires in 1 hour):\n{reset_link}\n\n"
        f"If you didn't request this, you can safely ignore this email."
    )
    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
    except Exception as exc:
        print(f"[reset] Email send failed ({exc}) — link for {to_email}: {reset_link}")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def _group_membership(cur, group_list_id: int, email: str):
    """Returns the member row (role, status) or None."""
    cur.execute("""
        SELECT role, status FROM group_list_members
        WHERE group_list_id = %s AND user_email = %s
    """, (group_list_id, email))
    return cur.fetchone()
 
def _require_active_member(cur, group_list_id: int, email: str):
    """404s if the list doesn't exist or the caller isn't an accepted member."""
    m = _group_membership(cur, group_list_id, email)
    if not m or m["status"] != "accepted":
        raise HTTPException(status_code=404, detail="Group list not found")
    return m

def _require_read_access(cur, group_list_id: int, email: str):
    """
    Accepted members always get in. Everyone else gets in only if the list
    is public. Returns the member row, or None for a public-list outsider.
    """
    m = _group_membership(cur, group_list_id, email)
    if m and m["status"] == "accepted":
        return m
    cur.execute("SELECT is_public FROM group_lists WHERE id = %s", (group_list_id,))
    gl = cur.fetchone()
    if not gl or not gl["is_public"]:
        raise HTTPException(status_code=404, detail="Group list not found")
    return None
 
def _are_friends(cur, a: str, b: str) -> bool:
    cur.execute("""
        SELECT 1 FROM friendships
        WHERE status = 'accepted'
          AND ((requester_email = %s AND addressee_email = %s)
            OR (requester_email = %s AND addressee_email = %s))
    """, (a, b, b, a))
    return cur.fetchone() is not None
 
def _is_following(cur, follower: str, followee: str) -> bool:
    """True if `follower` has an accepted follow of `followee`."""
    cur.execute("""
        SELECT 1 FROM friendships
        WHERE requester_email = %s AND addressee_email = %s AND status = 'accepted'
    """, (follower, followee))
    return cur.fetchone() is not None

def _post_tags(cur, post_type: str, post_id: int) -> list:
    """Companion tags on a post, as [{email, username}] in tag order."""
    cur.execute("""
        SELECT tagged_email FROM post_tags
        WHERE post_type = %s AND post_id = %s
        ORDER BY id ASC
    """, (post_type, post_id))
    return [{"email": r["tagged_email"], "username": username_from(r["tagged_email"])}
            for r in cur.fetchall()]

def _set_post_tags(cur, post_type: str, post_id: int, author: str, emails: list) -> None:
    """Sync a post's companion tags without re-notifying existing tags."""
    wanted, seen = [], set()
    for target in emails or []:
        target = (target or "").strip().lower()
        if not target or target == author or target in seen:
            continue
        if not _is_following(cur, author, target):
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

def _delete_post_extras(cur, post_type: str, post_id: int) -> None:
    cur.execute("DELETE FROM post_tags    WHERE post_type = %s AND post_id = %s", (post_type, post_id))
    cur.execute("DELETE FROM post_reposts WHERE post_type = %s AND post_id = %s", (post_type, post_id))


def _repost_state(cur, post_type: str, post_id: int, email: str) -> dict:
    cur.execute("""
        SELECT
          EXISTS (SELECT 1 FROM post_tags
                  WHERE post_type = %s AND post_id = %s AND tagged_email = %s)   AS is_tagged,
          EXISTS (SELECT 1 FROM post_reposts
                  WHERE post_type = %s AND post_id = %s AND reposter_email = %s) AS user_reposted
    """, (post_type, post_id, email) * 2)
    row = cur.fetchone()
    return {"is_tagged": bool(row["is_tagged"]), "user_reposted": bool(row["user_reposted"])}


def _feed_review(cur, review_id: int, viewer: str):
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
            "user_liked": bool(r["user_liked"]), "tagged": _post_tags(cur, "review", r["id"])}


def _feed_meal(cur, meal_id: int, viewer: str):
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
            "user_liked": bool(m["user_liked"]), "tagged": _post_tags(cur, "meal", m["id"])}


def _reposts_by(cur, reposter_emails: list, viewer: str, post_type=None, limit: int = 50) -> list:
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
        loader = _feed_review if rp["post_type"] == "review" else _feed_meal
        item = loader(cur, rp["post_id"], viewer)
        if item:
            out.append({**item,
                        "reposted_by": {"email": rp["reposter_email"],
                                        "username": username_from(rp["reposter_email"])},
                        "reposted_at": rp["created_at"]})
    return out


def _sort_at(item):
    return item.get("reposted_at") or item["logged_at"]

def _invite_friends(cur, group_list_id: int, inviter: str, emails: list) -> dict:
    """
    Inserts pending invites. Silently skips the inviter, non-friends, and
    anyone already invited or already a member. Re-invites people who declined.
    Returns {'invited': [...], 'skipped': [...]}.
    """
    invited, skipped = [], []
    for target in emails:
        if target == inviter:
            continue
        if not _are_friends(cur, inviter, target):
            skipped.append(target)
            continue
        existing = _group_membership(cur, group_list_id, target)
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

# ── Auth endpoints ────────────────────────────────────────────────────────────

@app.post("/signup", status_code=201)
def signup(body: SignupRequest, db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM users WHERE email = %s", (body.email,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")
        cur.execute(
            "INSERT INTO users (email, hashed_password) VALUES (%s, %s)",
            (body.email, hash_password(body.password))
        )
        db.commit()
    return {"message": "Account created. Please log in."}

@app.post("/login")
def login(body: LoginRequest, db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT * FROM users WHERE email = %s", (body.email,))
        user = cur.fetchone()
    if not user or not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"token": create_token(body.email), "email": body.email}

@app.get("/me")
def me(email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT is_private FROM users WHERE email = %s", (email,))
        row = cur.fetchone()
    return {"email": email, "is_private": bool(row["is_private"]) if row else False}

@app.post("/change-password")
def change_password(body: ChangePasswordRequest, email: str = Depends(get_current_user), db=Depends(get_db)):
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    with with_cursor(db) as cur:
        cur.execute("SELECT hashed_password FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        if not user or not verify_password(body.current_password, user["hashed_password"]):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        cur.execute("UPDATE users SET hashed_password = %s WHERE email = %s",
                    (hash_password(body.new_password), email))
        db.commit()
    return {"message": "Password updated."}

@app.patch("/me/privacy")
def update_privacy(body: PrivacyUpdate, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("UPDATE users SET is_private = %s WHERE email = %s RETURNING is_private",
                    (body.is_private, email))
        row = cur.fetchone()
        db.commit()
    return {"is_private": bool(row["is_private"])}

@app.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest, db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM users WHERE email = %s", (body.email,))
        user = cur.fetchone()
    # Only email real accounts, but always return the same message so the
    # endpoint can't be used to discover which emails are registered.
    if user:
        token = create_reset_token(body.email)
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        reset_link = f"{frontend_url}/reset-password?token={token}"
        send_reset_email(body.email, reset_link)
    return {"message": "If that email is registered, a reset link is on its way."}

@app.post("/reset-password")
def reset_password(body: ResetPasswordRequest, db=Depends(get_db)):
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    try:
        payload = jwt.decode(body.token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="This reset link has expired. Request a new one.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=400, detail="Invalid reset link.")
    if payload.get("purpose") != "reset":
        raise HTTPException(status_code=400, detail="Invalid reset link.")
    email = payload["sub"]
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Account not found")
        cur.execute("UPDATE users SET hashed_password = %s WHERE email = %s",
                    (hash_password(body.new_password), email))
        db.commit()
    return {"message": "Password updated. You can now log in."}


# ── Review endpoints ──────────────────────────────────────────────────────────

@app.post("/reviews", status_code=201, response_model=ReviewOut)
def create_review(body: ReviewCreate, email: str = Depends(get_current_user), db=Depends(get_db)):
    if body.type not in ("restaurant", "homemade"):
        raise HTTPException(status_code=400, detail="type must be 'restaurant' or 'homemade'")
    if not valid_rating(body.rating):
        raise HTTPException(status_code=400, detail="rating must be between 0.5 and 5 in half-star steps")

    # Recipe tagging only applies to homemade dishes. NULL means it's your own recipe.
    recipe_owner = body.recipe_owner_email.strip() if body.recipe_owner_email else None
    if recipe_owner and body.type != "homemade":
        raise HTTPException(status_code=400, detail="Only homemade dishes can tag a recipe author")
    if recipe_owner == email:
        recipe_owner = None  # tagging yourself just means it's your own recipe

    with with_cursor(db) as cur:
        if recipe_owner:
            cur.execute("SELECT id FROM users WHERE email = %s", (recipe_owner,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Tagged recipe author not found")
        cur.execute(
            """INSERT INTO dish_reviews (user_email, dish_name, type, restaurant_name, recipe, recipe_owner_email, rating, review)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING *""",
            (email, body.dish_name.strip(), body.type,
             body.restaurant_name.strip() if body.restaurant_name else None,
             body.recipe.strip() if body.recipe else None,
             recipe_owner,
             body.rating,
             body.review.strip() if body.review else None)
        )
        row = cur.fetchone()
        _set_post_tags(cur, "review", row["id"], email, body.tagged_emails)
        tagged = _post_tags(cur, "review", row["id"])
        db.commit()
    return {**dict(row), "tagged": tagged}

@app.get("/reviews", response_model=List[ReviewOut])
def get_reviews(email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT r.*,
                   COUNT(DISTINCT l.id) AS like_count,
                   COUNT(DISTINCT c.id) AS comment_count
            FROM dish_reviews r
            LEFT JOIN review_likes l ON l.review_id = r.id
            LEFT JOIN review_comments c ON c.review_id = r.id
            WHERE r.user_email = %s AND r.meal_id IS NULL
            GROUP BY r.id
            ORDER BY r.logged_at DESC
        """, (email,))
        rows = cur.fetchall()
        own = [{**dict(r), "tagged": _post_tags(cur, "review", r["id"])} for r in rows]
        reposts = _reposts_by(cur, [email], email, post_type="review", limit=200)
    return sorted(own + reposts, key=_sort_at, reverse=True)

@app.delete("/reviews/{review_id}", status_code=204)
def delete_review(review_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT meal_id FROM dish_reviews WHERE id = %s AND user_email = %s", (review_id, email))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Review not found")
        if row["meal_id"] is not None:
            raise HTTPException(status_code=400, detail="This dish is part of a meal — delete the meal instead")
        _delete_post_extras(cur, "review", review_id)
        cur.execute("DELETE FROM dish_reviews WHERE id = %s", (review_id,))
        db.commit()

@app.get("/reviews/{review_id}/detail")
def get_review_detail(review_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT r.*,
                   COUNT(DISTINCT l.id) AS like_count,
                   COUNT(DISTINCT c.id) AS comment_count,
                   COALESCE(BOOL_OR(l.user_email = %s), FALSE) AS user_liked
            FROM dish_reviews r
            LEFT JOIN review_likes l ON l.review_id = r.id
            LEFT JOIN review_comments c ON c.review_id = r.id
            WHERE r.id = %s
            GROUP BY r.id
        """, (email, review_id))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Review not found")
        tagged = _post_tags(cur, "review", review_id)
        repost = _repost_state(cur, "review", review_id, email)
    return {
        **serialise_review(row),
        "username":      username_from(row["user_email"]),
        "user_email":    row["user_email"],
        "like_count":    int(row["like_count"]),
        "comment_count": int(row["comment_count"]),
        "user_liked":    bool(row["user_liked"]),
        "meal_id":         row.get("meal_id"),
        "tagged":        tagged,
        **repost
    }

@app.post("/posts/{post_type}/{post_id}/repost")
def toggle_repost(post_type: str, post_id: int,
                  email: str = Depends(get_current_user), db=Depends(get_db)):
    if post_type not in ("review", "meal"):
        raise HTTPException(status_code=400, detail="post_type must be 'review' or 'meal'")
    with with_cursor(db) as cur:
        if post_type == "review":
            cur.execute("SELECT id FROM dish_reviews WHERE id = %s AND meal_id IS NULL", (post_id,))
        else:
            cur.execute("SELECT id FROM meals WHERE id = %s", (post_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Post not found")

        state = _repost_state(cur, post_type, post_id, email)
        if not state["is_tagged"]:
            raise HTTPException(status_code=403, detail="You can only repost posts you're tagged in")

        if state["user_reposted"]:
            cur.execute("""DELETE FROM post_reposts
                           WHERE post_type = %s AND post_id = %s AND reposter_email = %s""",
                        (post_type, post_id, email))
            reposted = False
        else:
            cur.execute("""INSERT INTO post_reposts (post_type, post_id, reposter_email)
                           VALUES (%s, %s, %s) ON CONFLICT DO NOTHING""",
                        (post_type, post_id, email))
            reposted = True
        db.commit()
    return {"reposted": reposted}

@app.patch("/reviews/{review_id}", response_model=ReviewOut)
def update_review(review_id: int, body: ReviewUpdate, email: str = Depends(get_current_user), db=Depends(get_db)):
    if body.type not in ("restaurant", "homemade"):
        raise HTTPException(status_code=400, detail="type must be 'restaurant' or 'homemade'")
    if not valid_rating(body.rating):
        raise HTTPException(status_code=400, detail="rating must be between 0.5 and 5 in half-star steps")

    recipe_owner = body.recipe_owner_email.strip() if body.recipe_owner_email else None
    if recipe_owner and body.type != "homemade":
        raise HTTPException(status_code=400, detail="Only homemade dishes can tag a recipe author")
    if recipe_owner == email:
        recipe_owner = None

    with with_cursor(db) as cur:
        cur.execute("SELECT meal_id FROM dish_reviews WHERE id = %s AND user_email = %s", (review_id, email))
        existing = cur.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Review not found")
        if existing["meal_id"] is not None:
            raise HTTPException(status_code=400, detail="This dish is part of a meal — edit the meal instead")
        if recipe_owner:
            cur.execute("SELECT id FROM users WHERE email = %s", (recipe_owner,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Tagged recipe author not found")
        cur.execute(
            """UPDATE dish_reviews
               SET dish_name = %s, type = %s, restaurant_name = %s, recipe = %s,
                   recipe_owner_email = %s, rating = %s, review = %s
               WHERE id = %s RETURNING *""",
            (body.dish_name.strip(), body.type,
             body.restaurant_name.strip() if body.restaurant_name else None,
             body.recipe.strip() if body.recipe else None,
             recipe_owner, body.rating,
             body.review.strip() if body.review else None,
             review_id)
        )
        row = cur.fetchone()
        _set_post_tags(cur, "review", review_id, email, body.tagged_emails)
        tagged = _post_tags(cur, "review", review_id)
        db.commit()
    return {**dict(row), "tagged": tagged}

@app.get("/reviews/{review_id}/likes")
def get_likes(review_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM dish_reviews WHERE id = %s", (review_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Review not found")
        cur.execute("""
            SELECT user_email, created_at FROM review_likes
            WHERE review_id = %s ORDER BY created_at DESC
        """, (review_id,))
        return [{
            "username":   username_from(r["user_email"]),
            "user_email": r["user_email"],
            "created_at": r["created_at"],
        } for r in cur.fetchall()]

# ── Likes & Comments ─────────────────────────────────────────────────────────

@app.post("/reviews/{review_id}/like")
def toggle_like(review_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM dish_reviews WHERE id = %s", (review_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Review not found")
        cur.execute("SELECT id FROM review_likes WHERE review_id = %s AND user_email = %s", (review_id, email))
        if cur.fetchone():
            cur.execute("DELETE FROM review_likes WHERE review_id = %s AND user_email = %s", (review_id, email))
            liked = False
        else:
            cur.execute("INSERT INTO review_likes (review_id, user_email) VALUES (%s, %s)", (review_id, email))
            liked = True
        cur.execute("SELECT COUNT(*) AS count FROM review_likes WHERE review_id = %s", (review_id,))
        count = cur.fetchone()["count"]
        db.commit()
    return {"liked": liked, "like_count": int(count)}

@app.get("/reviews/{review_id}/comments")
def get_comments(review_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM dish_reviews WHERE id = %s", (review_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Review not found")
        cur.execute("""
            SELECT c.id, c.user_email, c.content, c.created_at, c.parent_id,
                   COUNT(cl.id) AS like_count,
                   COALESCE(BOOL_OR(cl.user_email = %s), FALSE) AS user_liked
            FROM review_comments c
            LEFT JOIN review_comment_likes cl ON cl.comment_id = c.id
            WHERE c.review_id = %s
            GROUP BY c.id
            ORDER BY c.created_at ASC
        """, (email, review_id))
        return [{"id": r["id"], "username": username_from(r["user_email"]), "user_email": r["user_email"],
                 "content": r["content"], "created_at": r["created_at"], "parent_id": r["parent_id"],
                 "like_count": int(r["like_count"]), "user_liked": bool(r["user_liked"])}
                for r in cur.fetchall()]

@app.post("/reviews/{review_id}/comments", status_code=201)
def add_comment(review_id: int, body: CommentCreate, email: str = Depends(get_current_user), db=Depends(get_db)):
    if not body.content.strip():
        raise HTTPException(status_code=400, detail="Comment cannot be empty")
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM dish_reviews WHERE id = %s", (review_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Review not found")
        if body.parent_id is not None:
            cur.execute("SELECT id FROM review_comments WHERE id = %s AND review_id = %s",
                        (body.parent_id, review_id))
            if not cur.fetchone():
                raise HTTPException(status_code=400, detail="Parent comment not found")
        cur.execute(
            "INSERT INTO review_comments (review_id, user_email, content, parent_id) VALUES (%s, %s, %s, %s) RETURNING id, created_at",
            (review_id, email, body.content.strip(), body.parent_id)
        )
        row = cur.fetchone()
        db.commit()
    return {"id": row["id"], "username": username_from(email), "user_email": email,
            "content": body.content.strip(), "created_at": row["created_at"],
            "parent_id": body.parent_id, "like_count": 0, "user_liked": False}

@app.delete("/reviews/{review_id}/comments/{comment_id}", status_code=204)
def delete_comment(review_id: int, comment_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM review_comments WHERE id = %s AND review_id = %s AND user_email = %s",
                    (comment_id, review_id, email))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Comment not found")
        cur.execute("DELETE FROM review_comments WHERE id = %s", (comment_id,))
        db.commit()


# ── Comment likes ──────────────────────────────────────────────────────────────

@app.post("/comments/{comment_type}/{comment_id}/like")
def toggle_comment_like(comment_type: str, comment_id: int,
                        email: str = Depends(get_current_user), db=Depends(get_db)):
    if comment_type not in ("review", "meal"):
        raise HTTPException(status_code=400, detail="comment_type must be 'review' or 'meal'")
    # Table names come from a fixed whitelist, so interpolation here is safe.
    comment_table = "review_comments" if comment_type == "review" else "meal_comments"
    like_table    = "review_comment_likes" if comment_type == "review" else "meal_comment_likes"
    with with_cursor(db) as cur:
        cur.execute(f"SELECT id FROM {comment_table} WHERE id = %s", (comment_id,))
        if not cur.fetchone():
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


# ── User search ───────────────────────────────────────────────────────────────

@app.get("/users/search")
def search_users(q: str = "", email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT u.email, u.is_private, COUNT(r.id) AS review_count
            FROM users u
            LEFT JOIN dish_reviews r ON r.user_email = u.email
            WHERE u.email != %s AND u.email ILIKE %s
            GROUP BY u.email, u.is_private
            ORDER BY review_count DESC
            LIMIT 20
        """, (email, f"%{q}%"))
        users = cur.fetchall()

        result = []
        for u in users:
            # The follow button reflects only my outbound follow of this user.
            cur.execute("""
                SELECT status FROM friendships
                WHERE requester_email = %s AND addressee_email = %s
            """, (email, u["email"]))
            rel = cur.fetchone()

            if   rel is None:                  status = None
            elif rel["status"] == "accepted":  status = "following"
            elif rel["status"] == "pending":   status = "pending_sent"
            else:                              status = None   # declined

            result.append({
                "email":             u["email"],
                "username":          username_from(u["email"]),
                "review_count":      u["review_count"],
                "is_private":        bool(u["is_private"]),
                "friendship_status": status,
            })
    return result

@app.get("/users/{user_email}/reviews", response_model=List[ReviewOut])
def get_user_reviews(user_email: str, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM users WHERE email = %s", (user_email,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="User not found")
        cur.execute("""SELECT * FROM dish_reviews
                       WHERE user_email = %s AND meal_id IS NULL
                       ORDER BY logged_at DESC""", (user_email,))
        own = [{**dict(r), "tagged": _post_tags(cur, "review", r["id"])} for r in cur.fetchall()]
        reposts = _reposts_by(cur, [user_email], email, post_type="review", limit=200)
    return sorted(own + reposts, key=_sort_at, reverse=True)
    
@app.get("/users/{user_email}/friends")
def get_user_friends(user_email: str, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM users WHERE email = %s", (user_email,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="User not found")

        cur.execute("""
            SELECT f.addressee_email AS friend_email, COUNT(r.id) AS review_count
            FROM friendships f
            LEFT JOIN dish_reviews r ON r.user_email = f.addressee_email
            WHERE f.requester_email = %s AND f.status = 'accepted'
            GROUP BY f.addressee_email
        """, (user_email,))
        rows = cur.fetchall()
    return [{"email": r["friend_email"], "username": username_from(r["friend_email"]), "review_count": r["review_count"]} for r in rows]

@app.get("/users/{user_email}/lists")
def get_user_public_lists(user_email: str, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM users WHERE email = %s", (user_email,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="User not found")
        cur.execute("""
            SELECT cl.id, cl.name, cl.is_public, cl.created_at,
                   COUNT(li.id) AS item_count
            FROM custom_lists cl
            LEFT JOIN list_items li ON li.list_id = cl.id
            WHERE cl.user_email = %s AND cl.is_public = TRUE
            GROUP BY cl.id
            ORDER BY cl.created_at DESC
        """, (user_email,))
        return cur.fetchall()

@app.get("/users/{user_email}/group-lists")
def get_public_group_lists(user_email: str, email: str = Depends(get_current_user),
                           db=Depends(get_db)):
    """Public group lists this user is an accepted member of."""
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT gl.id, gl.name, gl.owner_email, gl.is_public, gl.created_at,
                   (SELECT COUNT(*) FROM group_list_members m
                     WHERE m.group_list_id = gl.id AND m.status = 'accepted') AS member_count,
                   (SELECT COUNT(*) FROM group_list_items i
                     WHERE i.group_list_id = gl.id) AS item_count
            FROM group_lists gl
            JOIN group_list_members me ON me.group_list_id = gl.id
            WHERE me.user_email = %s AND me.status = 'accepted' AND gl.is_public = TRUE
            ORDER BY gl.created_at DESC
        """, (user_email,))
        rows = cur.fetchall()
    return [{**dict(r), "owner_username": username_from(r["owner_email"])} for r in rows]
# ── Friend endpoints ──────────────────────────────────────────────────────────

@app.post("/friends/request", status_code=201)
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

@app.delete("/follow/{user_email}", status_code=204)
def unfollow(user_email: str, email: str = Depends(get_current_user), db=Depends(get_db)):
    """Stop following a user (removes my follow; leaves their follow of me intact)."""
    with with_cursor(db) as cur:
        cur.execute("""
            DELETE FROM friendships
            WHERE requester_email = %s AND addressee_email = %s
        """, (email, user_email))
        db.commit()

@app.get("/friends/requests/pending")
def get_pending_requests(email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT id, requester_email, created_at FROM friendships
            WHERE addressee_email = %s AND status = 'pending'
            ORDER BY created_at DESC
        """, (email,))
        return cur.fetchall()

@app.patch("/friends/requests/{request_id}", response_model=FriendRequestOut)
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

@app.get("/friends")
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


# ── Activity feed ─────────────────────────────────────────────────────────────

@app.get("/feed")
def get_feed(email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT addressee_email FROM friendships
            WHERE requester_email = %s AND status = 'accepted'
        """, (email,))
        friend_emails = [r["addressee_email"] for r in cur.fetchall()]
        if not friend_emails:
            return []
        placeholders = ",".join(["%s"] * len(friend_emails))

        cur.execute(f"""
            SELECT
                r.id, r.user_email, r.dish_name, r.type, r.restaurant_name,
                r.recipe, r.recipe_owner_email, r.rating, r.review, r.logged_at,
                COUNT(DISTINCT l.id) AS like_count,
                COUNT(DISTINCT c.id) AS comment_count,
                COALESCE(BOOL_OR(l.user_email = %s), FALSE) AS user_liked
            FROM dish_reviews r
            LEFT JOIN review_likes l ON l.review_id = r.id
            LEFT JOIN review_comments c ON c.review_id = r.id
            WHERE r.user_email IN ({placeholders}) AND r.meal_id IS NULL
            GROUP BY r.id
            ORDER BY r.logged_at DESC LIMIT 50
        """, [email] + friend_emails)

        review_rows = cur.fetchall()
        reviews = [{
            **serialise_review(r),
            "kind":          "review",
            "like_count":    int(r["like_count"]),
            "comment_count": int(r["comment_count"]),
            "user_liked":    bool(r["user_liked"]),
            "tagged":        _post_tags(cur, "review", r["id"]),
        } for r in review_rows]

        cur.execute(f"""
            SELECT m.*,
                   COUNT(DISTINCT l.id) AS like_count,
                   COUNT(DISTINCT c.id) AS comment_count,
                   COALESCE(BOOL_OR(l.user_email = %s), FALSE) AS user_liked
            FROM meals m
            LEFT JOIN meal_likes    l ON l.meal_id = m.id
            LEFT JOIN meal_comments c ON c.meal_id = m.id
            WHERE m.user_email IN ({placeholders})
            GROUP BY m.id
            ORDER BY m.logged_at DESC LIMIT 50
        """, [email] + friend_emails)
        meal_rows = cur.fetchall()

        meals = []
        for m in meal_rows:
            cur.execute("""
                SELECT id, dish_name, rating, review FROM dish_reviews
                WHERE meal_id = %s ORDER BY id ASC
            """, (m["id"],))
            dish_rows = cur.fetchall()
            meals.append({
                **serialise_meal(m, dish_rows),
                "like_count":    int(m["like_count"]),
                "comment_count": int(m["comment_count"]),
                "user_liked":    bool(m["user_liked"]),
                "tagged":        _post_tags(cur, "meal", m["id"]),
            })
            reposts = _reposts_by(cur, friend_emails, email)

    by_key = {}
    for item in reviews + meals + reposts:
        key = (item["kind"], item["id"])
        if key not in by_key or _sort_at(item) > _sort_at(by_key[key]):
            by_key[key] = item
    combined = sorted(by_key.values(), key=_sort_at, reverse=True)
    return combined[:50]


# ── All reviews (search) ──────────────────────────────────────────────────────

@app.get("/reviews/all")
def get_all_reviews(email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT r.*, u.email AS user_email
            FROM dish_reviews r JOIN users u ON u.email = r.user_email
            ORDER BY r.logged_at DESC
        """)
        return [serialise_review(r) for r in cur.fetchall()]


# ── Restaurant catalog ────────────────────────────────────────────────────────

@app.get("/restaurants")
def get_restaurants(email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT DISTINCT restaurant_name FROM dish_reviews
            WHERE type = 'restaurant' AND restaurant_name IS NOT NULL
            ORDER BY restaurant_name ASC
        """)
        return [r["restaurant_name"] for r in cur.fetchall()]

@app.get("/restaurants/{restaurant_name}/dishes")
def get_restaurant_dishes(restaurant_name: str, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT DISTINCT dish_name FROM dish_reviews
            WHERE type = 'restaurant' AND restaurant_name ILIKE %s
            ORDER BY dish_name ASC
        """, (restaurant_name,))
        return [r["dish_name"] for r in cur.fetchall()]

@app.get("/restaurants/{restaurant_name}/page")
def get_restaurant_page(restaurant_name: str, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT restaurant_name,
                   COUNT(*) AS total_reviews,
                   ROUND(AVG(rating)::numeric, 1) AS avg_rating,
                   COUNT(DISTINCT dish_name) AS total_dishes,
                   MIN(logged_at) AS first_logged,
                   (ARRAY_AGG(user_email ORDER BY logged_at ASC))[1] AS created_by
            FROM dish_reviews
            WHERE restaurant_name ILIKE %s AND type = 'restaurant'
            GROUP BY restaurant_name
        """, (restaurant_name,))
        stats = cur.fetchone()
        if not stats:
            raise HTTPException(status_code=404, detail="Restaurant not found")

        cur.execute("""
            SELECT dish_name, COUNT(*) AS review_count, ROUND(AVG(rating)::numeric,1) AS avg_rating
            FROM dish_reviews WHERE restaurant_name ILIKE %s AND type = 'restaurant'
            GROUP BY dish_name ORDER BY avg_rating DESC, review_count DESC
        """, (restaurant_name,))
        dishes = cur.fetchall()

        cur.execute("""
            SELECT id, user_email, dish_name, rating, review, logged_at, meal_id
            FROM dish_reviews WHERE restaurant_name ILIKE %s AND type = 'restaurant'
            ORDER BY logged_at DESC
        """, (restaurant_name,))
        reviews = cur.fetchall()

    return {
        "restaurant_name": stats["restaurant_name"],
        "total_reviews":   stats["total_reviews"],
        "avg_rating":      float(stats["avg_rating"]),
        "total_dishes":    stats["total_dishes"],
        "created_by":      username_from(stats["created_by"]),
        "created_by_email": stats["created_by"],
        "first_logged":    stats["first_logged"],
        "dishes":  [{"dish_name": d["dish_name"], "review_count": d["review_count"], "avg_rating": float(d["avg_rating"])} for d in dishes],
        "reviews": [serialise_review(r) for r in reviews],
    }


# ── Dish pages ────────────────────────────────────────────────────────────────

@app.get("/dishes")
def get_all_dishes(email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT dish_name, restaurant_name,
                   COUNT(*) AS review_count,
                   ROUND(AVG(rating)::numeric, 1) AS avg_rating,
                   MIN(logged_at) AS first_logged,
                   (ARRAY_AGG(user_email ORDER BY logged_at ASC))[1] AS created_by
            FROM dish_reviews
            WHERE type = 'restaurant' AND restaurant_name IS NOT NULL
            GROUP BY dish_name, restaurant_name
            ORDER BY review_count DESC, first_logged DESC
        """)
        rows = cur.fetchall()
    return [{"dish_name": r["dish_name"], "restaurant_name": r["restaurant_name"],
             "review_count": r["review_count"], "avg_rating": float(r["avg_rating"]),
             "created_by": username_from(r["created_by"]), "created_by_email": r["created_by"]} for r in rows]

@app.get("/search/dishes-restaurants")
def search_dishes_restaurants(q: str = "", item_type: str = "dish",
                              _email: str = Depends(get_current_user), db=Depends(get_db)):
    if not q.strip():
        return []
    pattern = f"%{q.strip()}%"
    with with_cursor(db) as cur:
        if item_type == "restaurant":
            cur.execute("""
                SELECT DISTINCT restaurant_name
                FROM dish_reviews
                WHERE type = 'restaurant'
                  AND restaurant_name IS NOT NULL
                  AND restaurant_name ILIKE %s
                ORDER BY restaurant_name
                LIMIT 10
            """, (pattern,))
            rows = cur.fetchall()
            return [{"name": r["restaurant_name"], "restaurant_name": None} for r in rows]
        else:
            cur.execute("""
                SELECT DISTINCT dish_name, restaurant_name
                FROM dish_reviews
                WHERE type = 'restaurant'
                  AND restaurant_name IS NOT NULL
                  AND (dish_name ILIKE %s OR restaurant_name ILIKE %s)
                ORDER BY dish_name
                LIMIT 10
            """, (pattern, pattern))
            rows = cur.fetchall()
            return [{"name": r["dish_name"], "restaurant_name": r["restaurant_name"]} for r in rows]

@app.get("/dishes/{dish_name}/restaurant/{restaurant_name}")
def get_dish_page(dish_name: str, restaurant_name: str, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT dish_name, restaurant_name,
                   COUNT(*) AS review_count,
                   ROUND(AVG(rating)::numeric, 1) AS avg_rating,
                   MIN(logged_at) AS first_logged,
                   (ARRAY_AGG(user_email ORDER BY logged_at ASC))[1] AS created_by
            FROM dish_reviews
            WHERE dish_name ILIKE %s AND restaurant_name ILIKE %s AND type = 'restaurant'
            GROUP BY dish_name, restaurant_name
        """, (dish_name, restaurant_name))
        stats = cur.fetchone()
        if not stats:
            raise HTTPException(status_code=404, detail="Dish not found")

        cur.execute("""
            SELECT id, user_email, rating, review, logged_at, meal_id FROM dish_reviews
            WHERE dish_name ILIKE %s AND restaurant_name ILIKE %s AND type = 'restaurant'
            ORDER BY logged_at DESC
        """, (dish_name, restaurant_name))
        reviews = cur.fetchall()

    return {
        "dish_name":        stats["dish_name"],
        "restaurant_name":  stats["restaurant_name"],
        "review_count":     stats["review_count"],
        "avg_rating":       float(stats["avg_rating"]),
        "created_by":       username_from(stats["created_by"]),
        "created_by_email": stats["created_by"],
        "first_logged":     stats["first_logged"],
        "reviews": [serialise_review(r) for r in reviews],
    }

@app.get("/recipes/page")
def get_recipe_page(dish_name: str, owner: str, email: str = Depends(get_current_user), db=Depends(get_db)):
    owner_filter = """
        type = 'homemade' AND dish_name ILIKE %s
        AND COALESCE(recipe_owner_email, user_email) = %s
    """
    with with_cursor(db) as cur:
        cur.execute(f"""
            SELECT MIN(dish_name) AS dish_name,
                   COUNT(*) AS review_count,
                   ROUND(AVG(rating)::numeric, 1) AS avg_rating,
                   MIN(logged_at) AS first_logged
            FROM dish_reviews WHERE {owner_filter}
        """, (dish_name, owner))
        stats = cur.fetchone()
        if not stats or stats["review_count"] == 0:
            raise HTTPException(status_code=404, detail="Recipe not found")

        # The recipe text: prefer the owner's own latest version, else anyone's
        cur.execute(f"""
            SELECT recipe FROM dish_reviews
            WHERE {owner_filter} AND recipe IS NOT NULL AND recipe <> ''
            ORDER BY (user_email = %s) DESC, logged_at DESC
            LIMIT 1
        """, (dish_name, owner, owner))
        recipe_row = cur.fetchone()

        cur.execute(f"""
            SELECT id, user_email, rating, review, logged_at, meal_id
            FROM dish_reviews WHERE {owner_filter}
            ORDER BY logged_at DESC
        """, (dish_name, owner))
        reviews = cur.fetchall()

    return {
        "dish_name":        stats["dish_name"],
        "restaurant_name":  None,
        "review_count":     stats["review_count"],
        "avg_rating":       float(stats["avg_rating"]),
        "created_by":       username_from(owner),
        "created_by_email": owner,
        "first_logged":     stats["first_logged"],
        "recipe":           recipe_row["recipe"] if recipe_row else "",
        "reviews":          [serialise_review(r) for r in reviews],
    }

    
# ── Trylist ───────────────────────────────────────────────────────────────────
# NOTE: /trylist/check must be defined before /trylist/{item_id}

@app.get("/trylist/check")
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

@app.get("/trylist")
def get_trylist(email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT id, item_type, dish_name, restaurant_name, added_at
            FROM trylists WHERE user_email = %s ORDER BY added_at DESC
        """, (email,))
        return cur.fetchall()

@app.post("/trylist", status_code=201)
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

@app.delete("/trylist/{item_id}", status_code=204)
def remove_from_trylist(item_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM trylists WHERE id = %s AND user_email = %s", (item_id, email))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Item not found")
        cur.execute("DELETE FROM trylists WHERE id = %s", (item_id,))
        db.commit()


# ── Custom Lists ──────────────────────────────────────────────────────────────

@app.get("/lists")
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

@app.post("/lists", status_code=201)
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

@app.delete("/lists/{list_id}", status_code=204)
def delete_list(list_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM custom_lists WHERE id = %s AND user_email = %s", (list_id, email))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="List not found")
        cur.execute("DELETE FROM custom_lists WHERE id = %s", (list_id,))
        db.commit()


@app.post("/lists/{list_id}/items", status_code=201)
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

        cur.execute(
            """INSERT INTO list_items (list_id, item_type, name, restaurant_name, note)
               VALUES (%s, %s, %s, %s, %s) RETURNING *""",
            (list_id, body.item_type, body.name.strip(), restaurant_name,
             body.note.strip() if body.note else None)
        )
        row = cur.fetchone()
        db.commit()
    return row

@app.delete("/lists/{list_id}/items/{item_id}", status_code=204)
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

@app.get("/lists/{list_id}/items")
def get_list_items(list_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute(
            "SELECT id FROM custom_lists WHERE id = %s AND (user_email = %s OR is_public = TRUE)",
            (list_id, email)
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="List not found")
        cur.execute(
            "SELECT * FROM list_items WHERE list_id = %s ORDER BY added_at ASC",
            (list_id,)
        )
        return cur.fetchall()


@app.get("/group-lists")
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
 
 
@app.get("/group-lists/invites")
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
 
 
@app.post("/group-lists", status_code=201)
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
        result = _invite_friends(cur, gl["id"], email, body.invite_emails)
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
 
 
@app.post("/group-lists/{list_id}/invite", status_code=201)
def invite_to_group_list(list_id: int, body: GroupInviteBody,
                         email: str = Depends(get_current_user), db=Depends(get_db)):
    """Any accepted member can pull in one of their own friends."""
    with with_cursor(db) as cur:
        _require_active_member(cur, list_id, email)
        result = _invite_friends(cur, list_id, email, body.emails)
        db.commit()
    return result
 
 
@app.patch("/group-lists/{list_id}/invite")
def respond_to_group_invite(list_id: int, body: GroupInviteAction,
                            email: str = Depends(get_current_user), db=Depends(get_db)):
    """
    Accept or decline. Declining only affects this member — the list stays alive
    for everyone who accepted, and anyone who never responds just stays pending.
    """
    if body.action not in ("accept", "decline"):
        raise HTTPException(status_code=400, detail="action must be 'accept' or 'decline'")
    with with_cursor(db) as cur:
        m = _group_membership(cur, list_id, email)
        if not m or m["status"] != "pending":
            raise HTTPException(status_code=404, detail="Invite not found")
        new_status = "accepted" if body.action == "accept" else "declined"
        cur.execute("""
            UPDATE group_list_members SET status = %s, responded_at = NOW()
            WHERE group_list_id = %s AND user_email = %s
        """, (new_status, list_id, email))
        db.commit()
    return {"group_list_id": list_id, "status": new_status}
 
@app.patch("/group-lists/{list_id}/visibility")
def set_group_list_visibility(list_id: int, body: GroupListVisibility,
                              email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        _require_active_member(cur, list_id, email)
        cur.execute("UPDATE group_lists SET is_public = %s WHERE id = %s RETURNING id, name, is_public",
                    (body.is_public, list_id))
        row = cur.fetchone()
        db.commit()
    return dict(row)
 
@app.get("/group-lists/{list_id}")
def get_group_list(list_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        me = _require_read_access(cur, list_id, email)
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
 
 
@app.get("/group-lists/{list_id}/items")
def get_group_list_items(list_id: int, email: str = Depends(get_current_user),
                         db=Depends(get_db)):
    with with_cursor(db) as cur:
        _require_read_access(cur, list_id, email)
        cur.execute("""
            SELECT * FROM group_list_items
            WHERE group_list_id = %s ORDER BY added_at ASC
        """, (list_id,))
        rows = cur.fetchall()
    return [{**dict(r), "added_by_username": username_from(r["added_by"])} for r in rows]
 
 
@app.post("/group-lists/{list_id}/items", status_code=201)
def add_group_list_item(list_id: int, body: GroupListItemCreate,
                        email: str = Depends(get_current_user), db=Depends(get_db)):
    if body.item_type not in ("dish", "restaurant", "recipe"):
        raise HTTPException(status_code=400,
                            detail="item_type must be 'dish', 'restaurant', or 'recipe'")
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="name cannot be empty")
    with with_cursor(db) as cur:
        _require_active_member(cur, list_id, email)
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
        cur.execute("""
            INSERT INTO group_list_items (group_list_id, added_by, item_type, name, restaurant_name, note)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING *
        """, (list_id, email, body.item_type, body.name.strip(), restaurant_name,
              body.note.strip() if body.note else None))
        row = cur.fetchone()
        db.commit()
    return {**dict(row), "added_by_username": username_from(email)}
 
 
@app.delete("/group-lists/{list_id}/items/{item_id}", status_code=204)
def remove_group_list_item(list_id: int, item_id: int,
                           email: str = Depends(get_current_user), db=Depends(get_db)):
    """You can remove what you added; the owner can remove anything."""
    with with_cursor(db) as cur:
        me = _require_active_member(cur, list_id, email)
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
 
 
@app.post("/group-lists/{list_id}/leave", status_code=204)
def leave_group_list(list_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        me = _require_active_member(cur, list_id, email)
        if me["role"] == "owner":
            raise HTTPException(status_code=400,
                                detail="Owners can't leave — delete the list instead")
        cur.execute("""
            UPDATE group_list_members SET status = 'declined', responded_at = NOW()
            WHERE group_list_id = %s AND user_email = %s
        """, (list_id, email))
        db.commit()
 
 
@app.delete("/group-lists/{list_id}", status_code=204)
def delete_group_list(list_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM group_lists WHERE id = %s AND owner_email = %s",
                    (list_id, email))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Group list not found")
        cur.execute("DELETE FROM group_lists WHERE id = %s", (list_id,))
        db.commit()

# ── Notifications ──────────────────────────────────────────────────────────────
@app.get("/notifications/activity")
def get_activity_notifications(email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT 'like' AS type, 'review' AS target_type, l.id AS event_id, l.created_at,
                   r.id AS target_id, l.user_email AS actor_email,
                   r.dish_name AS subject, r.restaurant_name
            FROM review_likes l
            JOIN dish_reviews r ON r.id = l.review_id
            WHERE r.user_email = %s AND l.user_email != %s AND r.meal_id IS NULL

            UNION ALL

            SELECT 'comment', 'review', c.id, c.created_at,
                   r.id, c.user_email, r.dish_name, r.restaurant_name
            FROM review_comments c
            JOIN dish_reviews r ON r.id = c.review_id
            WHERE r.user_email = %s AND c.user_email != %s AND r.meal_id IS NULL

            UNION ALL

            SELECT 'like', 'meal', l.id, l.created_at,
                   m.id, l.user_email, m.title, m.restaurant_name
            FROM meal_likes l
            JOIN meals m ON m.id = l.meal_id
            WHERE m.user_email = %s AND l.user_email != %s

            UNION ALL

            SELECT 'comment', 'meal', c.id, c.created_at,
                   m.id, c.user_email, m.title, m.restaurant_name
            FROM meal_comments c
            JOIN meals m ON m.id = c.meal_id
            WHERE m.user_email = %s AND c.user_email != %s
            UNION ALL

            SELECT 'tag', 'review', t.id, t.created_at,
                  r.id, r.user_email, r.dish_name, r.restaurant_name
            FROM post_tags t
            JOIN dish_reviews r ON t.post_type = 'review' AND r.id = t.post_id
            WHERE t.tagged_email = %s

            UNION ALL

            SELECT 'tag', 'meal', t.id, t.created_at,
                      m.id, m.user_email, m.title, m.restaurant_name
            FROM post_tags t
            JOIN meals m ON t.post_type = 'meal' AND m.id = t.post_id
            WHERE t.tagged_email = %s
            ORDER BY created_at DESC
            LIMIT 50
        """, (email,) * 10)
        rows = cur.fetchall()
        cur.execute("SELECT post_type, post_id FROM post_reposts WHERE reposter_email = %s", (email,))
        reposted = {(r["post_type"], r["post_id"]) for r in cur.fetchall()}
    return [{
        "id":              r["event_id"],
        "type":            r["type"],
        "target_type":     r["target_type"],
        "target_id":       r["target_id"],
        "actor_email":     r["actor_email"],
        "actor_username":  username_from(r["actor_email"]),
        "subject":         r["subject"],
        "restaurant_name": r["restaurant_name"],
        "created_at":      r["created_at"],
        "user_reposted": (r["target_type"], r["target_id"]) in reposted if r["type"] == "tag" else None,
    } for r in rows]

@app.get("/notifications/unseen_count")
def get_unseen_count(since: Optional[datetime] = None,
                     email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT COUNT(*) AS count FROM friendships
            WHERE addressee_email = %s AND status = 'pending'
        """, (email,))
        pending_count = cur.fetchone()["count"]
 
        # NEW: pending group list invites
        cur.execute("""
            SELECT COUNT(*) AS count FROM group_list_members
            WHERE user_email = %s AND status = 'pending'
        """, (email,))
        group_invite_count = cur.fetchone()["count"]
 
        since_val = since or datetime(1970, 1, 1)
        cur.execute("""
            SELECT COUNT(*) AS count FROM (
                SELECT l.id FROM review_likes l
                JOIN dish_reviews r ON r.id = l.review_id
                WHERE r.user_email = %s AND l.user_email != %s
                  AND l.created_at > %s AND r.meal_id IS NULL

                UNION ALL

                SELECT c.id FROM review_comments c
                JOIN dish_reviews r ON r.id = c.review_id
                WHERE r.user_email = %s AND c.user_email != %s
                  AND c.created_at > %s AND r.meal_id IS NULL

                UNION ALL

                SELECT l.id FROM meal_likes l
                JOIN meals m ON m.id = l.meal_id
                WHERE m.user_email = %s AND l.user_email != %s AND l.created_at > %s

                UNION ALL

                SELECT c.id FROM meal_comments c
                JOIN meals m ON m.id = c.meal_id
                WHERE m.user_email = %s AND c.user_email != %s AND c.created_at > %s
                UNION ALL

                SELECT t.id FROM post_tags t
                JOIN dish_reviews r ON t.post_type = 'review' AND r.id = t.post_id
                WHERE t.tagged_email = %s AND t.created_at > %s

                UNION ALL

                SELECT t.id FROM post_tags t
                JOIN meals m ON t.post_type = 'meal' AND m.id = t.post_id
                WHERE t.tagged_email = %s AND t.created_at > %s
            ) combined
        """, (email, email, since_val) * 4 + (email, since_val) * 2)
        activity_count = cur.fetchone()["count"]
 
    return {"count": pending_count + group_invite_count + activity_count}


# ── Meal endpoints ────────────────────────────────────────────────────────────

def _load_meal(cur, meal_id: int):
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


@app.post("/meals", status_code=201)
def create_meal(body: MealCreate, email: str = Depends(get_current_user), db=Depends(get_db)):
    restaurant = body.restaurant_name.strip()
    if not restaurant:
        raise HTTPException(status_code=400, detail="Restaurant is required")
    if not valid_rating(body.rating):
        raise HTTPException(status_code=400, detail="Overall rating must be between 0.5 and 5 in half-star steps")

    dishes, seen = [], set()
    for d in body.dishes:
        name = d.dish_name.strip()
        if not name:
            continue
        if name.lower() in seen:
            raise HTTPException(status_code=400, detail=f"'{name}' is listed twice")
        if not valid_rating(d.rating):
            raise HTTPException(status_code=400, detail=f"Rating for '{name}' must be between 0.5 and 5 in half-star steps")
        seen.add(name.lower())
        dishes.append((name, d.rating, (d.review or "").strip() or None))

    if not dishes:
        raise HTTPException(status_code=400, detail="A meal needs at least one rated dish")

    try:
        with with_cursor(db) as cur:
            cur.execute("""
                INSERT INTO meals (user_email, restaurant_name, title, rating, review)
                VALUES (%s, %s, %s, %s, %s) RETURNING *
            """, (email, restaurant, (body.title or "").strip() or None,
                  body.rating, (body.review or "").strip() or None))
            meal = cur.fetchone()

            dish_rows = []
            for name, dish_rating, note in dishes:
                cur.execute("""
                    INSERT INTO dish_reviews
                        (user_email, dish_name, type, restaurant_name, rating, review, meal_id)
                    VALUES (%s, %s, 'restaurant', %s, %s, %s, %s)
                    RETURNING id, dish_name, rating, review
                """, (email, name, restaurant, dish_rating, note, meal["id"]))
                dish_rows.append(cur.fetchone())
            _set_post_tags(cur, "meal", meal["id"], email, body.tagged_emails)
            tagged = _post_tags(cur, "meal", meal["id"])
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not save meal")

    return {**serialise_meal(meal, dish_rows), "tagged": tagged}


@app.get("/meals")
def get_my_meals(email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT * FROM meals WHERE user_email = %s ORDER BY logged_at DESC", (email,))
        meals = cur.fetchall()
        out = []
        for m in meals:
            cur.execute("""
                SELECT id, dish_name, rating, review FROM dish_reviews
                WHERE meal_id = %s ORDER BY id ASC
            """, (m["id"],))
            dish_rows = cur.fetchall()
            out.append({**serialise_meal(m, dish_rows), "tagged": _post_tags(cur, "meal", m["id"])})
        out += _reposts_by(cur, [email], email, post_type="meal", limit=200)
    out.sort(key=_sort_at, reverse=True)
    return out


@app.get("/meals/{meal_id}")
def get_meal(meal_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        meal, dish_rows = _load_meal(cur, meal_id)
        if not meal:
            raise HTTPException(status_code=404, detail="Meal not found")
        tagged = _post_tags(cur, "meal", meal_id)
        repost = _repost_state(cur, "meal", meal_id, email)
    return {**serialise_meal(meal, dish_rows), "tagged": tagged, **repost}


@app.delete("/meals/{meal_id}", status_code=204)
def delete_meal(meal_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM meals WHERE id = %s AND user_email = %s", (meal_id, email))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Meal not found")
        _delete_post_extras(cur, "meal", meal_id)
        cur.execute("DELETE FROM meals WHERE id = %s", (meal_id,))
        db.commit()

@app.patch("/meals/{meal_id}")
def update_meal(meal_id: int, body: MealCreate, email: str = Depends(get_current_user), db=Depends(get_db)):
    restaurant = body.restaurant_name.strip()
    if not restaurant:
        raise HTTPException(status_code=400, detail="Restaurant is required")
    if not valid_rating(body.rating):
        raise HTTPException(status_code=400, detail="Overall rating must be between 0.5 and 5 in half-star steps")

    dishes, seen = [], set()
    for d in body.dishes:
        name = d.dish_name.strip()
        if not name:
            continue
        if name.lower() in seen:
            raise HTTPException(status_code=400, detail=f"'{name}' is listed twice")
        if not valid_rating(d.rating):
            raise HTTPException(status_code=400, detail=f"Rating for '{name}' must be between 0.5 and 5 in half-star steps")
        seen.add(name.lower())
        dishes.append((d.id, name, d.rating, (d.review or "").strip() or None))
    if not dishes:
        raise HTTPException(status_code=400, detail="A meal needs at least one rated dish")

    try:
        with with_cursor(db) as cur:
            cur.execute("SELECT id FROM meals WHERE id = %s AND user_email = %s", (meal_id, email))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Meal not found")

            cur.execute("""
                UPDATE meals SET restaurant_name = %s, title = %s, rating = %s, review = %s
                WHERE id = %s RETURNING *
            """, (restaurant, (body.title or "").strip() or None,
                  body.rating, (body.review or "").strip() or None, meal_id))
            meal = cur.fetchone()

            cur.execute("SELECT id FROM dish_reviews WHERE meal_id = %s", (meal_id,))
            existing_ids = {r["id"] for r in cur.fetchall()}
            kept_ids = set()

            for dish_id, name, dish_rating, note in dishes:
                if dish_id in existing_ids:
                    cur.execute("""
                        UPDATE dish_reviews
                        SET dish_name = %s, restaurant_name = %s, rating = %s, review = %s
                        WHERE id = %s
                    """, (name, restaurant, dish_rating, note, dish_id))
                    kept_ids.add(dish_id)
                else:
                    cur.execute("""
                        INSERT INTO dish_reviews
                            (user_email, dish_name, type, restaurant_name, rating, review, meal_id)
                        VALUES (%s, %s, 'restaurant', %s, %s, %s, %s)
                    """, (email, name, restaurant, dish_rating, note, meal_id))

            removed = existing_ids - kept_ids
            if removed:
                cur.execute("DELETE FROM dish_reviews WHERE id = ANY(%s)", (list(removed),))

            _set_post_tags(cur, "meal", meal_id, email, body.tagged_emails)
            _, dish_rows = _load_meal(cur, meal_id)
            tagged = _post_tags(cur, "meal", meal_id)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not update meal")

    return {**serialise_meal(meal, dish_rows), "tagged": tagged}


@app.get("/users/{user_email}/meals")
def get_user_meals(user_email: str, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT * FROM meals WHERE user_email = %s ORDER BY logged_at DESC", (user_email,))
        meals = cur.fetchall()
        out = []
        for m in meals:
            cur.execute("""
                SELECT id, dish_name, rating, review FROM dish_reviews
                WHERE meal_id = %s ORDER BY id ASC
            """, (m["id"],))
            dish_rows = cur.fetchall()
            out.append({**serialise_meal(m, dish_rows), "tagged": _post_tags(cur, "meal", m["id"])})
        out += _reposts_by(cur, [user_email], email, post_type="meal", limit=200)
    out.sort(key=_sort_at, reverse=True)
    return out


@app.get("/meals/{meal_id}/detail")
def get_meal_detail(meal_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT m.*,
                   COUNT(DISTINCT l.id) AS like_count,
                   COUNT(DISTINCT c.id) AS comment_count,
                   COALESCE(BOOL_OR(l.user_email = %s), FALSE) AS user_liked
            FROM meals m
            LEFT JOIN meal_likes l ON l.meal_id = m.id
            LEFT JOIN meal_comments c ON c.meal_id = m.id
            WHERE m.id = %s
            GROUP BY m.id
        """, (email, meal_id))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Meal not found")
        cur.execute("""
            SELECT id, dish_name, rating, review FROM dish_reviews
            WHERE meal_id = %s ORDER BY id ASC
        """, (meal_id,))
        dish_rows = cur.fetchall()
        tagged = _post_tags(cur, "meal", meal_id)
    return {
        **serialise_meal(row, dish_rows),
        "like_count":    int(row["like_count"]),
        "comment_count": int(row["comment_count"]),
        "user_liked":    bool(row["user_liked"]),
        "tagged":        tagged,
    }


@app.post("/meals/{meal_id}/like")
def toggle_meal_like(meal_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM meals WHERE id = %s", (meal_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Meal not found")
        cur.execute("SELECT id FROM meal_likes WHERE meal_id = %s AND user_email = %s", (meal_id, email))
        if cur.fetchone():
            cur.execute("DELETE FROM meal_likes WHERE meal_id = %s AND user_email = %s", (meal_id, email))
            liked = False
        else:
            cur.execute("INSERT INTO meal_likes (meal_id, user_email) VALUES (%s, %s)", (meal_id, email))
            liked = True
        cur.execute("SELECT COUNT(*) AS count FROM meal_likes WHERE meal_id = %s", (meal_id,))
        count = cur.fetchone()["count"]
        db.commit()
    return {"liked": liked, "like_count": int(count)}


@app.get("/meals/{meal_id}/likes")
def get_meal_likes(meal_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT user_email, created_at FROM meal_likes
            WHERE meal_id = %s ORDER BY created_at DESC
        """, (meal_id,))
        return [{
            "username":   username_from(r["user_email"]),
            "user_email": r["user_email"],
            "created_at": r["created_at"],
        } for r in cur.fetchall()]


@app.get("/meals/{meal_id}/comments")
def get_meal_comments(meal_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT c.id, c.user_email, c.content, c.created_at, c.parent_id,
                   COUNT(cl.id) AS like_count,
                   COALESCE(BOOL_OR(cl.user_email = %s), FALSE) AS user_liked
            FROM meal_comments c
            LEFT JOIN meal_comment_likes cl ON cl.comment_id = c.id
            WHERE c.meal_id = %s
            GROUP BY c.id
            ORDER BY c.created_at ASC
        """, (email, meal_id))
        return [{
            "id":         r["id"],
            "username":   username_from(r["user_email"]),
            "user_email": r["user_email"],
            "content":    r["content"],
            "created_at": r["created_at"],
            "parent_id":  r["parent_id"],
            "like_count": int(r["like_count"]),
            "user_liked": bool(r["user_liked"]),
        } for r in cur.fetchall()]


@app.post("/meals/{meal_id}/comments", status_code=201)
def add_meal_comment(meal_id: int, body: CommentCreate,
                     email: str = Depends(get_current_user), db=Depends(get_db)):
    content = body.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Comment cannot be empty")
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM meals WHERE id = %s", (meal_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Meal not found")
        if body.parent_id is not None:
            cur.execute("SELECT id FROM meal_comments WHERE id = %s AND meal_id = %s",
                        (body.parent_id, meal_id))
            if not cur.fetchone():
                raise HTTPException(status_code=400, detail="Parent comment not found")
        cur.execute("""
            INSERT INTO meal_comments (meal_id, user_email, content, parent_id)
            VALUES (%s, %s, %s, %s) RETURNING id, created_at
        """, (meal_id, email, content, body.parent_id))
        row = cur.fetchone()
        db.commit()
    return {"id": row["id"], "username": username_from(email), "user_email": email,
            "content": content, "created_at": row["created_at"],
            "parent_id": body.parent_id, "like_count": 0, "user_liked": False}


@app.delete("/meals/{meal_id}/comments/{comment_id}", status_code=204)
def delete_meal_comment(meal_id: int, comment_id: int,
                        email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM meal_comments WHERE id = %s AND meal_id = %s AND user_email = %s",
                    (comment_id, meal_id, email))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Comment not found")
        cur.execute("DELETE FROM meal_comments WHERE id = %s", (comment_id,))
        db.commit()