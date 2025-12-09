"""Authentication schemas."""
from pydantic import BaseModel, EmailStr, Field
from app.models.enums import Role


class UserRegister(BaseModel):
    """User registration schema."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str = Field(..., min_length=1, max_length=255)
    organization_name: str = Field(..., min_length=1, max_length=255)


class UserLogin(BaseModel):
    """User login schema."""
    email: EmailStr
    password: str


class Token(BaseModel):
    """JWT token response schema."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """JWT token payload data."""
    user_id: str
    email: str
    role: Role
    organization_id: str | None = None

