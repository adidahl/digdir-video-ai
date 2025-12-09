"""Enum types for database models."""
import enum


class Role(str, enum.Enum):
    """User role enum."""
    SUPER_ADMIN = "super_admin"
    ORG_ADMIN = "org_admin"
    USER = "user"


class SecurityLevel(str, enum.Enum):
    """Video security level enum."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    SECRET = "secret"


class VideoStatus(str, enum.Enum):
    """Video processing status enum."""
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PermissionType(str, enum.Enum):
    """Access permission type enum."""
    VIEW = "view"
    EDIT = "edit"
    ADMIN = "admin"

