"""Signup, login, password reset and account settings."""

import os

import jwt
from fastapi import APIRouter, Depends, HTTPException

from app.core.config import ALGORITHM, SECRET_KEY
from app.core.db import get_db
from app.core.security import create_reset_token, create_token, get_current_user, hash_password, verify_password
from app.schemas.auth import ChangePasswordRequest, ForgotPasswordRequest, LoginRequest, PrivacyUpdate, ResetPasswordRequest, SignupRequest
from app.services.email import send_reset_email
from app.utils import with_cursor

router = APIRouter()


@router.post("/signup", status_code=201)
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


@router.post("/login")
def login(body: LoginRequest, db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT * FROM users WHERE email = %s", (body.email,))
        user = cur.fetchone()
    if not user or not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"token": create_token(body.email), "email": body.email}


@router.get("/me")
def me(email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("SELECT is_private FROM users WHERE email = %s", (email,))
        row = cur.fetchone()
    return {"email": email, "is_private": bool(row["is_private"]) if row else False}


@router.post("/change-password")
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


@router.patch("/me/privacy")
def update_privacy(body: PrivacyUpdate, email: str = Depends(get_current_user), db=Depends(get_db)):
    with with_cursor(db) as cur:
        cur.execute("UPDATE users SET is_private = %s WHERE email = %s RETURNING is_private",
                    (body.is_private, email))
        row = cur.fetchone()
        db.commit()
    return {"is_private": bool(row["is_private"])}


@router.post("/forgot-password")
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


@router.post("/reset-password")
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
