"""User schemas."""
from pydantic import BaseModel, EmailStr, UUID4, Field
from datetime import datetime
from typing import Optional
from app.models.enums import Role


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    full_name: str


class UserCreate(UserBase):
    """User creation schema."""
    password: str = Field(..., min_length=8, max_length=100)
    role: Role = Role.USER
    organization_id: Optional[UUID4] = None


class UserUpdate(BaseModel):
    """User update schema."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[Role] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """User response schema."""
    id: UUID4
    role: Role
    organization_id: Optional[UUID4]
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class OrganizationBase(BaseModel):
    """Base organization schema."""
    name: str


class OrganizationCreate(OrganizationBase):
    """Organization creation schema."""
    pass


class OrganizationResponse(OrganizationBase):
    """Organization response schema."""
    id: UUID4
    created_at: datetime
    
    class Config:
        from_attributes = True

