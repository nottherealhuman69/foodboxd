"""Models shared by reviews and meals."""

from typing import Optional

from pydantic import BaseModel


class CommentCreate(BaseModel):
    content: str
    parent_id: Optional[int] = None
