"""User management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.user import UserResponse, UserCreate, UserUpdate
from app.models.user import User
from app.models.enums import Role
from app.dependencies import get_current_active_user, get_org_admin, get_super_admin
from app.utils.security import get_password_hash
import uuid

router = APIRouter()


@router.get("/", response_model=List[UserResponse])
async def list_users(
    current_user: User = Depends(get_org_admin),
    db: Session = Depends(get_db)
):
    """List users in the organization (org admin+)."""
    if current_user.role == Role.SUPER_ADMIN:
        users = db.query(User).all()
    else:
        users = db.query(User).filter(
            User.organization_id == current_user.organization_id
        ).all()
    
    return users


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_org_admin),
    db: Session = Depends(get_db)
):
    """Create a new user (org admin+)."""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Org admin can only create users in their own organization
    if current_user.role == Role.ORG_ADMIN:
        if user_data.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create users in other organizations"
            )
        # Org admin cannot create super admins
        if user_data.role == Role.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create super admin users"
            )
    
    user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role,
        organization_id=user_data.organization_id,
        is_active=True
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user by ID."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Only allow viewing users in same organization (unless super admin)
    if current_user.role != Role.SUPER_ADMIN:
        if user.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    user_update: UserUpdate,
    current_user: User = Depends(get_org_admin),
    db: Session = Depends(get_db)
):
    """Update user (org admin+)."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Org admin can only update users in their own organization
    if current_user.role == Role.ORG_ADMIN:
        if user.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot update users in other organizations"
            )
    
    # Update fields
    if user_update.email is not None:
        user.email = user_update.email
    if user_update.full_name is not None:
        user.full_name = user_update.full_name
    if user_update.role is not None:
        user.role = user_update.role
    if user_update.is_active is not None:
        user.is_active = user_update.is_active
    
    db.commit()
    db.refresh(user)
    
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """Delete user (super admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    db.delete(user)
    db.commit()
    
    return None

