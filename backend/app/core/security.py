"""Password hashing, JWT creation/decoding and the current-user dependency."""

from datetime import datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import ALGORITHM, SECRET_KEY


security  = HTTPBearer()


def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_token(email: str) -> str:
    payload = {"sub": email, "exp": datetime.utcnow() + timedelta(hours=24)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_reset_token(email: str) -> str:
    payload = {"sub": email, "purpose": "reset",
               "exp": datetime.utcnow() + timedelta(hours=1)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
