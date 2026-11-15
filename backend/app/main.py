"""FastAPI application: middleware, startup and router registration."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import CORS_ORIGINS
from app.db.schema import create_tables
from app.routers import (
    auth, feed, group_lists, lists, meals, notifications,
    places, posts, reviews, social, trylist, users,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    create_tables()
    yield


app = FastAPI(title="Dishlog API", lifespan=lifespan)

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
