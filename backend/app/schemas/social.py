"""Request/response models for follows and friend requests."""

from datetime import datetime

from pydantic import BaseModel, EmailStr


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
