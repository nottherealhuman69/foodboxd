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
            CREATE TABLE IF NOT EXISTS user_lists (
                id         SERIAL PRIMARY KEY,
                user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                name       VARCHAR(255) NOT NULL,
                is_public  BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS list_items (
                id              SERIAL PRIMARY KEY,
                list_id         INTEGER NOT NULL REFERENCES user_lists(id) ON DELETE CASCADE,
                item_type       VARCHAR(20) NOT NULL CHECK (item_type IN ('dish', 'restaurant', 'recipe')),
                name            VARCHAR(255) NOT NULL,
                restaurant_name VARCHAR(255),
                note            TEXT,
                added_at        TIMESTAMP DEFAULT NOW()
            )
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

class ListCreate(BaseModel):
    name: str
    is_public: bool = True

class ListItemCreate(BaseModel):
    item_type: str
    name: str
    restaurant_name: Optional[str] = None
    note: Optional[str] = None


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
        cur.execute("SELECT * FROM dish_reviews WHERE user_email = %s ORDER BY logged_at DESC", (email,))
        return cur.fetchall()

@app.delete("/reviews/{review_id}", status_code=204)
def delete_review(review_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM dish_reviews WHERE id = %s AND user_email = %s", (review_id, email))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Review not found")
        cur.execute("DELETE FROM dish_reviews WHERE id = %s", (review_id,))
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
            SELECT id, user_email, dish_name, type, restaurant_name, rating, review, logged_at
            FROM dish_reviews WHERE user_email IN ({placeholders})
            ORDER BY logged_at DESC LIMIT 50
        """, friend_emails)
        return [serialise_review(r) for r in cur.fetchall()]


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
            SELECT l.id, l.name, l.is_public, l.created_at,
                   COUNT(i.id) AS item_count
            FROM user_lists l
            LEFT JOIN list_items i ON i.list_id = l.id
            WHERE l.user_email = %s
            GROUP BY l.id
            ORDER BY l.created_at DESC
        """, (email,))
        return cur.fetchall()

@app.post("/lists", status_code=201)
def create_list(body: ListCreate, email: str = Depends(get_current_user), db=Depends(get_db)):
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="name is required")
    with with_cursor(db) as cur:
        cur.execute(
            "INSERT INTO user_lists (user_email, name, is_public) VALUES (%s, %s, %s) RETURNING id, name, is_public, created_at",
            (email, body.name.strip(), body.is_public)
        )
        row = cur.fetchone()
        db.commit()
    return row

@app.delete("/lists/{list_id}", status_code=204)
def delete_list(list_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM user_lists WHERE id = %s AND user_email = %s", (list_id, email))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="List not found")
        cur.execute("DELETE FROM user_lists WHERE id = %s", (list_id,))
        db.commit()

@app.get("/lists/{list_id}/items")
def get_list_items(list_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM user_lists WHERE id = %s AND user_email = %s", (list_id, email))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="List not found")
        cur.execute("""
            SELECT id, item_type, name, restaurant_name, note, added_at
            FROM list_items WHERE list_id = %s ORDER BY added_at ASC
        """, (list_id,))
        return cur.fetchall()

@app.post("/lists/{list_id}/items", status_code=201)
def add_list_item(list_id: int, body: ListItemCreate, email: str = Depends(get_current_user), db=Depends(get_db)):
    if body.item_type not in ("dish", "restaurant", "recipe"):
        raise HTTPException(status_code=400, detail="item_type must be 'dish', 'restaurant', or 'recipe'")
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="name is required")
    with with_cursor(db) as cur:
        cur.execute("SELECT id FROM user_lists WHERE id = %s AND user_email = %s", (list_id, email))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="List not found")
        cur.execute(
            """INSERT INTO list_items (list_id, item_type, name, restaurant_name, note)
               VALUES (%s, %s, %s, %s, %s) RETURNING id, item_type, name, restaurant_name, note, added_at""",
            (list_id, body.item_type, body.name.strip(),
             body.restaurant_name.strip() if body.restaurant_name else None,
             body.note.strip() if body.note else None)
        )
        row = cur.fetchone()
        db.commit()
    return row

@app.delete("/lists/{list_id}/items/{item_id}", status_code=204)
def delete_list_item(list_id: int, item_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("""
            SELECT i.id FROM list_items i
            JOIN user_lists l ON l.id = i.list_id
            WHERE i.id = %s AND i.list_id = %s AND l.user_email = %s
        """, (item_id, list_id, email))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Item not found")
        cur.execute("DELETE FROM list_items WHERE id = %s", (item_id,))
        db.commit()
