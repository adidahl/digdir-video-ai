"""FastAPI dependencies for authentication and authorization."""
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models.user import User
from app.models.enums import Role
from app.services.auth import decode_access_token
import uuid

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token."""
    token = credentials.credentials
    
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user from header or query parameter (for video streaming)."""
    from fastapi import Query
    
    # Try to get token from header first
    auth_header = request.headers.get("Authorization")
    token = None
    
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    else:
        # Try query parameter as fallback (for video elements)
        token = request.query_params.get("token")
    
    if not token:
        return None
    
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id:
            user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
            if user and user.is_active:
                return user
    except Exception:
        pass
    
    return None


async def require_role(required_role: Role):
    """Dependency to require specific user role."""
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role == Role.SUPER_ADMIN:
            return current_user
        
        if current_user.role == required_role:
            return current_user
        
        # ORG_ADMIN has more privileges than USER
        if required_role == Role.USER and current_user.role == Role.ORG_ADMIN:
            return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Required role: {required_role.value}"
        )
    
    return role_checker


async def get_super_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Require super admin role."""
    if current_user.role != Role.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    return current_user


async def get_org_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Require organization admin role or higher."""
    if current_user.role not in [Role.SUPER_ADMIN, Role.ORG_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization admin access required"
        )
    return current_user

