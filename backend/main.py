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
from utils import with_cursor, serialise_review, username_from
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
    rating: int
    review: Optional[str] = None

class ReviewOut(BaseModel):
    id: int
    dish_name: str
    type: str
    restaurant_name: Optional[str]
    recipe: Optional[str]
    rating: int
    review: Optional[str]
    logged_at: datetime
    like_count: int = 0
    comment_count: int = 0

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

class TrylistAdd(BaseModel):
    item_type: str
    dish_name: Optional[str] = None
    restaurant_name: Optional[str] = None

class CommentCreate(BaseModel):
    content: str

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
def me(email: str = Depends(get_current_user)):
    return {"email": email}


# ── Review endpoints ──────────────────────────────────────────────────────────

@app.post("/reviews", status_code=201, response_model=ReviewOut)
def create_review(body: ReviewCreate, email: str = Depends(get_current_user), db=Depends(get_db)):
    if body.type not in ("restaurant", "homemade"):
        raise HTTPException(status_code=400, detail="type must be 'restaurant' or 'homemade'")
    if not 1 <= body.rating <= 5:
        raise HTTPException(status_code=400, detail="rating must be between 1 and 5")
    with with_cursor(db) as cur:
        cur.execute(
            """INSERT INTO dish_reviews (user_email, dish_name, type, restaurant_name, recipe, rating, review)
               VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *""",
            (email, body.dish_name.strip(), body.type,
             body.restaurant_name.strip() if body.restaurant_name else None,
             body.recipe.strip() if body.recipe else None,
             body.rating,
             body.review.strip() if body.review else None)
        )
        row = cur.fetchone()
        db.commit()
    return row

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
            WHERE r.user_email = %s
            GROUP BY r.id
            ORDER BY r.logged_at DESC
        """, (email,))
        return cur.fetchall()

@app.delete("/reviews/{review_id}", status_code=204)
def delete_review(review_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM dish_reviews WHERE id = %s AND user_email = %s", (review_id, email))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Review not found")
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
    return {
        **serialise_review(row),
        "username":      username_from(row["user_email"]),
        "user_email":    row["user_email"],
        "like_count":    int(row["like_count"]),
        "comment_count": int(row["comment_count"]),
        "user_liked":    bool(row["user_liked"]),
    }

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
            SELECT id, user_email, content, created_at
            FROM review_comments WHERE review_id = %s ORDER BY created_at ASC
        """, (review_id,))
        return [{"id": r["id"], "username": username_from(r["user_email"]), "user_email": r["user_email"],
                 "content": r["content"], "created_at": r["created_at"]} for r in cur.fetchall()]

@app.post("/reviews/{review_id}/comments", status_code=201)
def add_comment(review_id: int, body: CommentCreate, email: str = Depends(get_current_user), db=Depends(get_db)):
    if not body.content.strip():
        raise HTTPException(status_code=400, detail="Comment cannot be empty")
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM dish_reviews WHERE id = %s", (review_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Review not found")
        cur.execute(
            "INSERT INTO review_comments (review_id, user_email, content) VALUES (%s, %s, %s) RETURNING id, created_at",
            (review_id, email, body.content.strip())
        )
        row = cur.fetchone()
        db.commit()
    return {"id": row["id"], "username": username_from(email), "user_email": email,
            "content": body.content.strip(), "created_at": row["created_at"]}

@app.delete("/reviews/{review_id}/comments/{comment_id}", status_code=204)
def delete_comment(review_id: int, comment_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM review_comments WHERE id = %s AND review_id = %s AND user_email = %s",
                    (comment_id, review_id, email))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Comment not found")
        cur.execute("DELETE FROM review_comments WHERE id = %s", (comment_id,))
        db.commit()


# ── User search ───────────────────────────────────────────────────────────────

@app.get("/users/search")
def search_users(q: str = "", email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT u.email, COUNT(r.id) AS review_count
            FROM users u
            LEFT JOIN dish_reviews r ON r.user_email = u.email
            WHERE u.email != %s AND u.email ILIKE %s
            GROUP BY u.email
            ORDER BY review_count DESC
            LIMIT 20
        """, (email, f"%{q}%"))
        users = cur.fetchall()

        result = []
        for u in users:
            cur.execute("""
                SELECT status, requester_email FROM friendships
                WHERE (requester_email = %s AND addressee_email = %s)
                   OR (requester_email = %s AND addressee_email = %s)
            """, (email, u["email"], u["email"], email))
            rel = cur.fetchone()

            if rel is None:                             status = None
            elif rel["status"] == "accepted":           status = "accepted"
            elif rel["status"] == "declined":           status = None
            elif rel["requester_email"] == email:       status = "pending_sent"
            else:                                       status = "pending_received"

            result.append({
                "email":             u["email"],
                "username":          username_from(u["email"]),
                "review_count":      u["review_count"],
                "friendship_status": status,
            })
    return result

@app.get("/users/{user_email}/reviews", response_model=List[ReviewOut])
def get_user_reviews(user_email: str, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM users WHERE email = %s", (user_email,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="User not found")
        cur.execute("SELECT * FROM dish_reviews WHERE user_email = %s ORDER BY logged_at DESC", (user_email,))
        return cur.fetchall()
    
@app.get("/users/{user_email}/friends")
def get_user_friends(user_email: str, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM users WHERE email = %s", (user_email,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="User not found")

        cur.execute("""
            SELECT
                CASE WHEN requester_email = %s THEN addressee_email ELSE requester_email END AS friend_email,
                COUNT(r.id) AS review_count
            FROM friendships f
            LEFT JOIN dish_reviews r
                ON r.user_email = CASE WHEN f.requester_email = %s THEN f.addressee_email ELSE f.requester_email END
            WHERE (requester_email = %s OR addressee_email = %s) AND status = 'accepted'
            GROUP BY friend_email
        """, (user_email, user_email, user_email, user_email))
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
    if body.addressee_email == email:
        raise HTTPException(status_code=400, detail="Cannot send request to yourself")
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM users WHERE email = %s", (body.addressee_email,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="User not found")
        cur.execute("""
            SELECT id, status FROM friendships
            WHERE (requester_email = %s AND addressee_email = %s)
               OR (requester_email = %s AND addressee_email = %s)
        """, (email, body.addressee_email, body.addressee_email, email))
        existing = cur.fetchone()
        if existing and existing["status"] == "pending":
            raise HTTPException(status_code=409, detail="Request already pending")
        if existing and existing["status"] == "accepted":
            raise HTTPException(status_code=409, detail="Already friends")
        cur.execute(
            "INSERT INTO friendships (requester_email, addressee_email) VALUES (%s, %s) RETURNING *",
            (email, body.addressee_email)
        )
        row = cur.fetchone()
        db.commit()
    return row

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
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT
                CASE WHEN requester_email = %s THEN addressee_email ELSE requester_email END AS friend_email,
                COUNT(r.id) AS review_count
            FROM friendships f
            LEFT JOIN dish_reviews r
                ON r.user_email = CASE WHEN f.requester_email = %s THEN f.addressee_email ELSE f.requester_email END
            WHERE (requester_email = %s OR addressee_email = %s) AND status = 'accepted'
            GROUP BY friend_email
        """, (email, email, email, email))
        rows = cur.fetchall()
    return [{"email": r["friend_email"], "username": username_from(r["friend_email"]), "review_count": r["review_count"]} for r in rows]


# ── Activity feed ─────────────────────────────────────────────────────────────

@app.get("/feed")
def get_feed(email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT requester_email, addressee_email FROM friendships
            WHERE (requester_email = %s OR addressee_email = %s) AND status = 'accepted'
        """, (email, email))
        friend_emails = [
            r["addressee_email"] if r["requester_email"] == email else r["requester_email"]
            for r in cur.fetchall()
        ]
        if not friend_emails:
            return []
        placeholders = ",".join(["%s"] * len(friend_emails))
        cur.execute(f"""
            SELECT
                r.id, r.user_email, r.dish_name, r.type, r.restaurant_name, r.rating, r.review, r.logged_at,
                COUNT(DISTINCT l.id) AS like_count,
                COUNT(DISTINCT c.id) AS comment_count,
                COALESCE(BOOL_OR(l.user_email = %s), FALSE) AS user_liked
            FROM dish_reviews r
            LEFT JOIN review_likes l ON l.review_id = r.id
            LEFT JOIN review_comments c ON c.review_id = r.id
            WHERE r.user_email IN ({placeholders})
            GROUP BY r.id
            ORDER BY r.logged_at DESC LIMIT 50
        """, [email] + friend_emails)
        return [{
            **serialise_review(r),
            "like_count":    int(r["like_count"]),
            "comment_count": int(r["comment_count"]),
            "user_liked":    bool(r["user_liked"]),
        } for r in cur.fetchall()]


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
            SELECT id, user_email, dish_name, rating, review, logged_at
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
            SELECT id, user_email, rating, review, logged_at FROM dish_reviews
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
            SELECT 'like' AS type, l.id, l.user_email AS actor_email, l.created_at,
                   r.id AS review_id, r.dish_name, r.restaurant_name
            FROM review_likes l
            JOIN dish_reviews r ON r.id = l.review_id
            WHERE r.user_email = %s AND l.user_email != %s

            UNION ALL

            SELECT 'comment' AS type, c.id, c.user_email AS actor_email, c.created_at,
                   r.id AS review_id, r.dish_name, r.restaurant_name
            FROM review_comments c
            JOIN dish_reviews r ON r.id = c.review_id
            WHERE r.user_email = %s AND c.user_email != %s

            ORDER BY created_at DESC
            LIMIT 50
        """, (email, email, email, email))
        rows = cur.fetchall()
    return [{
        "type": r["type"],
        "actor_email": r["actor_email"],
        "actor_username": username_from(r["actor_email"]),
        "review_id": r["review_id"],
        "dish_name": r["dish_name"],
        "restaurant_name": r["restaurant_name"],
        "created_at": r["created_at"],
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
                WHERE r.user_email = %s AND l.user_email != %s AND l.created_at > %s
 
                UNION ALL
 
                SELECT c.id FROM review_comments c
                JOIN dish_reviews r ON r.id = c.review_id
                WHERE r.user_email = %s AND c.user_email != %s AND c.created_at > %s
            ) combined
        """, (email, email, since_val, email, email, since_val))
        activity_count = cur.fetchone()["count"]
 
    return {"count": pending_count + group_invite_count + activity_count}