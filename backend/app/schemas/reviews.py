"""Request/response models for dish reviews."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr


class IngredientIn(BaseModel):
    name: str
    quantity: float
    unit: str


class ReviewCreate(BaseModel):
    dish_name: str
    type: str
    restaurant_name: Optional[str] = None
    recipe: Optional[str] = None
    recipe_owner_email: Optional[str] = None
    rating: float
    review: Optional[str] = None
    tagged_emails: List[EmailStr] = []
    forked_from_id: Optional[int] = None
    ingredients: List[IngredientIn] = []


class ReviewUpdate(BaseModel):
    dish_name: str
    type: str
    restaurant_name: Optional[str] = None
    recipe: Optional[str] = None
    recipe_owner_email: Optional[str] = None
    rating: float
    review: Optional[str] = None
    tagged_emails: List[EmailStr] = []
    ingredients: List[IngredientIn] = []


class ReviewOut(BaseModel):
    id: int
    user_email: Optional[str] = None
    dish_name: str
    type: str
    restaurant_name: Optional[str]
    recipe: Optional[str]
    recipe_owner_email: Optional[str] = None
    rating: float
    review: Optional[str]
    logged_at: datetime
    like_count: int = 0
    comment_count: int = 0
    tagged: List[dict] = []
    reposted_by: Optional[dict] = None
    reposted_at: Optional[datetime] = None
    forked_from_id: Optional[int] = None
    ingredients: List[dict] = []
