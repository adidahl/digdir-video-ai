"""Admin endpoints for organization and system management."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.user import OrganizationResponse, OrganizationCreate, UserResponse
from app.models.user import Organization, User
from app.models.video import Video
from app.models.enums import Role
from app.dependencies import get_super_admin, get_org_admin
import uuid

router = APIRouter()


@router.get("/organizations", response_model=List[OrganizationResponse])
async def list_organizations(
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """List all organizations (super admin only)."""
    organizations = db.query(Organization).all()
    return organizations


@router.post("/organizations", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_data: OrganizationCreate,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """Create a new organization (super admin only)."""
    # Check if organization already exists
    existing_org = db.query(Organization).filter(
        Organization.name == org_data.name
    ).first()
    
    if existing_org:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization already exists"
        )
    
    organization = Organization(name=org_data.name)
    db.add(organization)
    db.commit()
    db.refresh(organization)
    
    return organization


@router.get("/organizations/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: uuid.UUID,
    current_user: User = Depends(get_org_admin),
    db: Session = Depends(get_db)
):
    """Get organization details."""
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Org admins can only view their own organization
    if current_user.role == Role.ORG_ADMIN:
        if current_user.organization_id != org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    return organization


@router.get("/organizations/{org_id}/users", response_model=List[UserResponse])
async def list_organization_users(
    org_id: uuid.UUID,
    current_user: User = Depends(get_org_admin),
    db: Session = Depends(get_db)
):
    """List users in an organization."""
    # Org admins can only view users in their own organization
    if current_user.role == Role.ORG_ADMIN:
        if current_user.organization_id != org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    users = db.query(User).filter(User.organization_id == org_id).all()
    return users


@router.get("/organizations/{org_id}/stats")
async def get_organization_stats(
    org_id: uuid.UUID,
    current_user: User = Depends(get_org_admin),
    db: Session = Depends(get_db)
):
    """Get organization statistics."""
    # Org admins can only view stats for their own organization
    if current_user.role == Role.ORG_ADMIN:
        if current_user.organization_id != org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    # Get counts
    user_count = db.query(User).filter(User.organization_id == org_id).count()
    video_count = db.query(Video).filter(Video.organization_id == org_id).count()
    
    return {
        "organization_id": str(org_id),
        "user_count": user_count,
        "video_count": video_count
    }


@router.delete("/organizations/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    org_id: uuid.UUID,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """Delete an organization (super admin only)."""
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check if organization has users or videos
    user_count = db.query(User).filter(User.organization_id == org_id).count()
    video_count = db.query(Video).filter(Video.organization_id == org_id).count()
    
    if user_count > 0 or video_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete organization with {user_count} users and {video_count} videos"
        )
    
    db.delete(organization)
    db.commit()
    
    return None

