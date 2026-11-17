"""Request models for meals."""

from typing import List, Optional

from pydantic import BaseModel, EmailStr


class MealDishIn(BaseModel):
    id: Optional[int] = None
    dish_name: str
    rating: float
    review: Optional[str] = None


class MealCreate(BaseModel):
    restaurant_name: str
    title: Optional[str] = None
    rating: float
    review: Optional[str] = None
    dishes: List[MealDishIn]
    tagged_emails: List[EmailStr] = []
    forked_from_id: Optional[int] = None
