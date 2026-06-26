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

load_dotenv()

app = FastAPI(title="Dishlog API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/authdb")


def get_db():
    conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()


def create_tables():
    conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
    cur = conn.cursor()

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

    conn.commit()
    cur.close()
    conn.close()


create_tables()


# ── Models ────────────────────────────────────────────────────────────────────

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
    action: str  # 'accept' | 'decline'

class FriendRequestOut(BaseModel):
    id: int
    requester_email: str
    addressee_email: str
    status: str
    created_at: datetime

class UserSearchOut(BaseModel):
    email: str
    username: str
    review_count: int
    friendship_status: Optional[str] = None  # 'pending_sent' | 'pending_received' | 'accepted' | None


# ── Helpers ───────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

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
    cur = db.cursor()
    cur.execute("SELECT id FROM users WHERE email = %s", (body.email,))
    if cur.fetchone():
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = hash_password(body.password)
    cur.execute("INSERT INTO users (email, hashed_password) VALUES (%s, %s)", (body.email, hashed))
    db.commit()
    cur.close()
    return {"message": "Account created. Please log in."}

@app.post("/login")
def login(body: LoginRequest, db=Depends(get_db)):
    cur = db.cursor()
    cur.execute("SELECT * FROM users WHERE email = %s", (body.email,))
    user = cur.fetchone()
    cur.close()
    if not user or not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token(body.email)
    return {"token": token, "email": body.email}

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
    cur = db.cursor()
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
    cur.close()
    return row

@app.get("/reviews", response_model=List[ReviewOut])
def get_reviews(email: str = Depends(get_current_user), db=Depends(get_db)):
    cur = db.cursor()
    cur.execute("SELECT * FROM dish_reviews WHERE user_email = %s ORDER BY logged_at DESC", (email,))
    rows = cur.fetchall()
    cur.close()
    return rows

@app.delete("/reviews/{review_id}", status_code=204)
def delete_review(review_id: int, email: str = Depends(get_current_user), db=Depends(get_db)):
    cur = db.cursor()
    cur.execute("SELECT id FROM dish_reviews WHERE id = %s AND user_email = %s", (review_id, email))
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="Review not found")
    cur.execute("DELETE FROM dish_reviews WHERE id = %s", (review_id,))
    db.commit()
    cur.close()


# ── User search endpoint ──────────────────────────────────────────────────────

@app.get("/users/search")
def search_users(q: str = "", email: str = Depends(get_current_user), db=Depends(get_db)):
    cur = db.cursor()
    # Find all users except self, with review counts
    cur.execute("""
        SELECT u.email,
               u.email AS username,
               COUNT(r.id) AS review_count
        FROM users u
        LEFT JOIN dish_reviews r ON r.user_email = u.email
        WHERE u.email != %s
          AND u.email ILIKE %s
        GROUP BY u.email
        ORDER BY review_count DESC
        LIMIT 20
    """, (email, f"%{q}%"))
    users = cur.fetchall()

    # Get friendship statuses between current user and found users
    result = []
    for u in users:
        cur.execute("""
            SELECT status, requester_email
            FROM friendships
            WHERE (requester_email = %s AND addressee_email = %s)
               OR (requester_email = %s AND addressee_email = %s)
        """, (email, u["email"], u["email"], email))
        rel = cur.fetchone()

        if rel is None:
            status = None
        elif rel["status"] == "accepted":
            status = "accepted"
        elif rel["status"] == "declined":
            status = None
        elif rel["requester_email"] == email:
            status = "pending_sent"
        else:
            status = "pending_received"

        result.append({
            "email": u["email"],
            "username": u["email"].split("@")[0],
            "review_count": u["review_count"],
            "friendship_status": status,
        })

    cur.close()
    return result


# ── Friend request endpoints ──────────────────────────────────────────────────

@app.post("/friends/request", status_code=201)
def send_friend_request(body: FriendRequestBody, email: str = Depends(get_current_user), db=Depends(get_db)):
    if body.addressee_email == email:
        raise HTTPException(status_code=400, detail="Cannot send request to yourself")

    cur = db.cursor()
    # Check addressee exists
    cur.execute("SELECT id FROM users WHERE email = %s", (body.addressee_email,))
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="User not found")

    # Check no existing request
    cur.execute("""
        SELECT id, status FROM friendships
        WHERE (requester_email = %s AND addressee_email = %s)
           OR (requester_email = %s AND addressee_email = %s)
    """, (email, body.addressee_email, body.addressee_email, email))
    existing = cur.fetchone()
    if existing:
        if existing["status"] == "accepted":
            raise HTTPException(status_code=400, detail="Already friends")
        if existing["status"] == "pending":
            raise HTTPException(status_code=400, detail="Request already pending")

    cur.execute(
        "INSERT INTO friendships (requester_email, addressee_email) VALUES (%s, %s) RETURNING *",
        (email, body.addressee_email)
    )
    row = cur.fetchone()
    db.commit()
    cur.close()
    return row


@app.get("/friends/requests/pending")
def get_pending_requests(email: str = Depends(get_current_user), db=Depends(get_db)):
    """Returns incoming pending requests (other people requesting to follow you)."""
    cur = db.cursor()
    cur.execute("""
        SELECT f.id, f.requester_email, f.created_at,
               COUNT(r.id) AS review_count
        FROM friendships f
        LEFT JOIN dish_reviews r ON r.user_email = f.requester_email
        WHERE f.addressee_email = %s AND f.status = 'pending'
        GROUP BY f.id, f.requester_email, f.created_at
        ORDER BY f.created_at DESC
    """, (email,))
    rows = cur.fetchall()
    cur.close()
    return [
        {
            "id": r["id"],
            "requester_email": r["requester_email"],
            "username": r["requester_email"].split("@")[0],
            "review_count": r["review_count"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


@app.patch("/friends/requests/{request_id}")
def respond_to_request(
    request_id: int,
    body: FriendActionBody,
    email: str = Depends(get_current_user),
    db=Depends(get_db)
):
    if body.action not in ("accept", "decline"):
        raise HTTPException(status_code=400, detail="action must be 'accept' or 'decline'")

    cur = db.cursor()
    cur.execute(
        "SELECT * FROM friendships WHERE id = %s AND addressee_email = %s AND status = 'pending'",
        (request_id, email)
    )
    req = cur.fetchone()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    new_status = "accepted" if body.action == "accept" else "declined"
    cur.execute(
        "UPDATE friendships SET status = %s, updated_at = NOW() WHERE id = %s RETURNING *",
        (new_status, request_id)
    )
    row = cur.fetchone()
    db.commit()
    cur.close()
    return row


@app.get("/friends")
def get_friends(email: str = Depends(get_current_user), db=Depends(get_db)):
    """Returns all accepted friends."""
    cur = db.cursor()
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
    cur.close()
    return [
        {
            "email": r["friend_email"],
            "username": r["friend_email"].split("@")[0],
            "review_count": r["review_count"],
        }
        for r in rows
    ]


# ── Public user reviews endpoint ──────────────────────────────────────────────

@app.get("/users/{user_email}/reviews", response_model=List[ReviewOut])
def get_user_reviews(
    user_email: str,
    email: str = Depends(get_current_user),
    db=Depends(get_db)
):
    """Returns another user's reviews. Available to anyone who is logged in."""
    cur = db.cursor()
    cur.execute("SELECT id FROM users WHERE email = %s", (user_email,))
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="User not found")
    cur.execute(
        "SELECT * FROM dish_reviews WHERE user_email = %s ORDER BY logged_at DESC",
        (user_email,)
    )
    rows = cur.fetchall()
    cur.close()
    return rows


# ── All reviews (for search) ──────────────────────────────────────────────────

@app.get("/reviews/all")
def get_all_reviews(email: str = Depends(get_current_user), db=Depends(get_db)):
    """Returns all reviews from all users for the search page."""
    cur = db.cursor()
    cur.execute("""
        SELECT r.*, u.email AS author_email
        FROM dish_reviews r
        JOIN users u ON u.email = r.user_email
        ORDER BY r.logged_at DESC
    """)
    rows = cur.fetchall()
    cur.close()
    return [
        {
            "id":              row["id"],
            "dish_name":       row["dish_name"],
            "type":            row["type"],
            "restaurant_name": row["restaurant_name"],
            "rating":          row["rating"],
            "review":          row["review"],
            "logged_at":       row["logged_at"],
            "user_email":      row["author_email"],
        }
        for row in rows
    ]


# ── Dish pages ────────────────────────────────────────────────────────────────

@app.get("/dishes")
def get_all_dishes(email: str = Depends(get_current_user), db=Depends(get_db)):
    """Returns unique (dish_name, restaurant_name) combos with aggregate stats."""
    cur = db.cursor()
    cur.execute("""
        SELECT
            dish_name,
            restaurant_name,
            COUNT(*)                                      AS review_count,
            ROUND(AVG(rating)::numeric, 1)               AS avg_rating,
            MIN(logged_at)                               AS first_logged,
            (ARRAY_AGG(user_email ORDER BY logged_at ASC))[1] AS created_by
        FROM dish_reviews
        WHERE type = 'restaurant' AND restaurant_name IS NOT NULL
        GROUP BY dish_name, restaurant_name
        ORDER BY review_count DESC, first_logged DESC
    """)
    rows = cur.fetchall()
    cur.close()
    return [
        {
            "dish_name":     r["dish_name"],
            "restaurant_name": r["restaurant_name"],
            "review_count":  r["review_count"],
            "avg_rating":    float(r["avg_rating"]),
            "created_by":    r["created_by"].split("@")[0],
            "created_by_email": r["created_by"],
        }
        for r in rows
    ]


@app.get("/dishes/{dish_name}/restaurant/{restaurant_name}")
def get_dish_page(
    dish_name: str,
    restaurant_name: str,
    email: str = Depends(get_current_user),
    db=Depends(get_db)
):
    """Returns full dish page: stats + all reviews for this dish at this restaurant."""
    cur = db.cursor()

    # Aggregate stats
    cur.execute("""
        SELECT
            dish_name,
            restaurant_name,
            COUNT(*)                                      AS review_count,
            ROUND(AVG(rating)::numeric, 1)               AS avg_rating,
            MIN(logged_at)                               AS first_logged,
            (ARRAY_AGG(user_email ORDER BY logged_at ASC))[1] AS created_by
        FROM dish_reviews
        WHERE dish_name ILIKE %s AND restaurant_name ILIKE %s AND type = 'restaurant'
        GROUP BY dish_name, restaurant_name
    """, (dish_name, restaurant_name))
    stats = cur.fetchone()

    if not stats:
        raise HTTPException(status_code=404, detail="Dish not found")

    # All reviews for this dish
    cur.execute("""
        SELECT id, user_email, rating, review, logged_at
        FROM dish_reviews
        WHERE dish_name ILIKE %s AND restaurant_name ILIKE %s AND type = 'restaurant'
        ORDER BY logged_at DESC
    """, (dish_name, restaurant_name))
    reviews = cur.fetchall()
    cur.close()

    return {
        "dish_name":        stats["dish_name"],
        "restaurant_name":  stats["restaurant_name"],
        "review_count":     stats["review_count"],
        "avg_rating":       float(stats["avg_rating"]),
        "created_by":       stats["created_by"].split("@")[0],
        "created_by_email": stats["created_by"],
        "first_logged":     stats["first_logged"],
        "reviews": [
            {
                "id":        r["id"],
                "username":  r["user_email"].split("@")[0],
                "user_email": r["user_email"],
                "rating":    r["rating"],
                "review":    r["review"] or "",
                "logged_at": r["logged_at"],
            }
            for r in reviews
        ],
    }


# ── Restaurant + dish catalog endpoints ───────────────────────────────────────

@app.get("/restaurants")
def get_restaurants(email: str = Depends(get_current_user), db=Depends(get_db)):
    """All unique restaurant names across all reviews."""
    cur = db.cursor()
    cur.execute("""
        SELECT DISTINCT restaurant_name
        FROM dish_reviews
        WHERE type = 'restaurant' AND restaurant_name IS NOT NULL
        ORDER BY restaurant_name ASC
    """)
    rows = cur.fetchall()
    cur.close()
    return [r["restaurant_name"] for r in rows]


@app.get("/restaurants/{restaurant_name}/dishes")
def get_restaurant_dishes(
    restaurant_name: str,
    email: str = Depends(get_current_user),
    db=Depends(get_db)
):
    """All unique dish names logged at a specific restaurant."""
    cur = db.cursor()
    cur.execute("""
        SELECT DISTINCT dish_name
        FROM dish_reviews
        WHERE type = 'restaurant'
          AND restaurant_name ILIKE %s
        ORDER BY dish_name ASC
    """, (restaurant_name,))
    rows = cur.fetchall()
    cur.close()
    return [r["dish_name"] for r in rows]