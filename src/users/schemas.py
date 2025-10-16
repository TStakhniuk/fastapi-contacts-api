from datetime import datetime
from pydantic import BaseModel


class UserProfileResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    created_at: datetime
    avatar: str | None = None

    class Config:
        from_attributes = True
