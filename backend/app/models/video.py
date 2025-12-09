"""Video and related models."""
from sqlalchemy import Column, String, Text, Float, ForeignKey, DateTime, Integer, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import uuid
from app.database import Base
from app.models.enums import SecurityLevel, VideoStatus, PermissionType


class Video(Base):
    """Video model."""
    __tablename__ = "videos"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    file_path = Column(String(1000), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    security_level = Column(Enum(SecurityLevel), nullable=False, default=SecurityLevel.INTERNAL)
    video_metadata = Column(JSON, default=dict)  # Renamed from 'metadata' to avoid SQLAlchemy conflict
    status = Column(Enum(VideoStatus), nullable=False, default=VideoStatus.UPLOADING)
    duration = Column(Float, nullable=True)  # Duration in seconds
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    organization = relationship("Organization", back_populates="videos")
    uploader = relationship("User", back_populates="uploaded_videos", foreign_keys=[uploaded_by])
    segments = relationship("VideoSegment", back_populates="video", cascade="all, delete-orphan")
    access_permissions = relationship("VideoAccessPermission", back_populates="video", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Video(id={self.id}, title={self.title}, status={self.status})>"


class VideoSegment(Base):
    """Video segment model with transcription and embeddings."""
    __tablename__ = "video_segments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id"), nullable=False, index=True)
    segment_id = Column(Integer, nullable=False)
    start_time = Column(Float, nullable=False)  # Start time in seconds
    end_time = Column(Float, nullable=False)  # End time in seconds
    text = Column(Text, nullable=False)
    embedding = Column(Vector(1536))  # OpenAI embedding dimension
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    video = relationship("Video", back_populates="segments")
    
    def __repr__(self):
        return f"<VideoSegment(id={self.id}, video_id={self.video_id}, segment_id={self.segment_id})>"


class VideoAccessPermission(Base):
    """Fine-grained access control for videos."""
    __tablename__ = "video_access_permissions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True)
    permission_type = Column(Enum(PermissionType), nullable=False, default=PermissionType.VIEW)
    granted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    video = relationship("Video", back_populates="access_permissions")
    user = relationship("User", back_populates="access_permissions", foreign_keys=[user_id])
    granter = relationship("User", foreign_keys=[granted_by])
    
    def __repr__(self):
        return f"<VideoAccessPermission(id={self.id}, video_id={self.video_id}, permission={self.permission_type})>"

