"""Request models for trylists, custom lists and group lists."""

from typing import List, Optional

from pydantic import BaseModel, EmailStr


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
    recipe_owner_email: Optional[str] = None


class GroupListCreate(BaseModel):
    name: str
    invite_emails: List[EmailStr] = []
    is_public: bool = False
    recipe_owner_email: Optional[str] = None


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
