"""FastAPI application: middleware and router registration.

The database schema is managed by Alembic (backend/migrations/), not at startup.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import CORS_ORIGINS
from app.routers import (
    auth, feed, group_lists, lists, meals, notifications,
    places, posts, reviews, social, trylist, users,
)

app = FastAPI(title="Dishlog API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (auth, reviews, posts, users, social, feed, places,
               trylist, lists, group_lists, notifications, meals):
    app.include_router(module.router)
