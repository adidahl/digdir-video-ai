"""Access control service for video permissions."""
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.video import Video, VideoAccessPermission
from app.models.enums import Role, SecurityLevel, PermissionType
from typing import List, Optional


def can_access_video(user: User, video: Video, db: Session) -> bool:
    """Check if a user can access a video.
    
    Access rules:
    1. Super admin can access all videos
    2. Org admin can access all videos in their organization
    3. Regular user can access videos based on organization + security level + explicit permissions
    """
    # Super admin can access all
    if user.role == Role.SUPER_ADMIN:
        return True
    
    # Org admin can access all in their org
    if user.role == Role.ORG_ADMIN and user.organization_id == video.organization_id:
        return True
    
    # Check if user belongs to the same organization
    if user.organization_id != video.organization_id:
        return False
    
    # Check explicit permissions
    explicit_permission = db.query(VideoAccessPermission).filter(
        VideoAccessPermission.video_id == video.id,
        VideoAccessPermission.user_id == user.id
    ).first()
    
    if explicit_permission:
        return True
    
    # Check security clearance based on security level
    return check_security_clearance(user, video.security_level)


def check_security_clearance(user: User, security_level: SecurityLevel) -> bool:
    """Check if user has clearance for a given security level.
    
    For now, all users in the org can access public and internal.
    Confidential and secret require explicit permissions or admin role.
    """
    if security_level in [SecurityLevel.PUBLIC, SecurityLevel.INTERNAL]:
        return True
    
    # Confidential and secret require admin role
    if user.role in [Role.ORG_ADMIN, Role.SUPER_ADMIN]:
        return True
    
    return False


def can_edit_video(user: User, video: Video, db: Session) -> bool:
    """Check if a user can edit a video."""
    # Super admin can edit all
    if user.role == Role.SUPER_ADMIN:
        return True
    
    # Org admin can edit all in their org
    if user.role == Role.ORG_ADMIN and user.organization_id == video.organization_id:
        return True
    
    # Video uploader can edit their own videos
    if video.uploaded_by == user.id:
        return True
    
    # Check explicit edit permissions
    edit_permission = db.query(VideoAccessPermission).filter(
        VideoAccessPermission.video_id == video.id,
        VideoAccessPermission.user_id == user.id,
        VideoAccessPermission.permission_type.in_([PermissionType.EDIT, PermissionType.ADMIN])
    ).first()
    
    return edit_permission is not None


def filter_accessible_videos(user: User, videos: List[Video], db: Session) -> List[Video]:
    """Filter a list of videos to only those the user can access."""
    # Super admin can access all
    if user.role == Role.SUPER_ADMIN:
        return videos
    
    accessible = []
    for video in videos:
        if can_access_video(user, video, db):
            accessible.append(video)
    
    return accessible

