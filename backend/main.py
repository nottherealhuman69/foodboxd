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

    conn.commit()
    cur.close()
    conn.close()


create_tables()


# ── Auth models ──────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ── Review models ─────────────────────────────────────────────────────────────

class ReviewCreate(BaseModel):
    dish_name: str
    type: str                        # 'restaurant' | 'homemade'
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


# ── Helpers ───────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def create_token(email: str) -> str:
    payload = {
        "sub": email,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
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
    cur.execute(
        "INSERT INTO users (email, hashed_password) VALUES (%s, %s)",
        (body.email, hashed)
    )
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
def create_review(
    body: ReviewCreate,
    email: str = Depends(get_current_user),
    db=Depends(get_db)
):
    if body.type not in ("restaurant", "homemade"):
        raise HTTPException(status_code=400, detail="type must be 'restaurant' or 'homemade'")
    if not 1 <= body.rating <= 5:
        raise HTTPException(status_code=400, detail="rating must be between 1 and 5")

    cur = db.cursor()
    cur.execute(
        """
        INSERT INTO dish_reviews
            (user_email, dish_name, type, restaurant_name, recipe, rating, review)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING *
        """,
        (
            email,
            body.dish_name.strip(),
            body.type,
            body.restaurant_name.strip() if body.restaurant_name else None,
            body.recipe.strip() if body.recipe else None,
            body.rating,
            body.review.strip() if body.review else None,
        )
    )
    row = cur.fetchone()
    db.commit()
    cur.close()
    return row


@app.get("/reviews", response_model=List[ReviewOut])
def get_reviews(
    email: str = Depends(get_current_user),
    db=Depends(get_db)
):
    cur = db.cursor()
    cur.execute(
        "SELECT * FROM dish_reviews WHERE user_email = %s ORDER BY logged_at DESC",
        (email,)
    )
    rows = cur.fetchall()
    cur.close()
    return rows


@app.delete("/reviews/{review_id}", status_code=204)
def delete_review(
    review_id: int,
    email: str = Depends(get_current_user),
    db=Depends(get_db)
):
    cur = db.cursor()
    cur.execute(
        "SELECT id FROM dish_reviews WHERE id = %s AND user_email = %s",
        (review_id, email)
    )
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="Review not found")
    cur.execute("DELETE FROM dish_reviews WHERE id = %s", (review_id,))
    db.commit()
    cur.close()