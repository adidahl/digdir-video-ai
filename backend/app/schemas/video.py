"""Video schemas."""
from pydantic import BaseModel, UUID4, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.models.enums import SecurityLevel, VideoStatus


class VideoBase(BaseModel):
    """Base video schema."""
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    security_level: SecurityLevel = SecurityLevel.INTERNAL


class VideoCreate(VideoBase):
    """Video creation schema."""
    video_metadata: Optional[Dict[str, Any]] = {}


class VideoUpdate(BaseModel):
    """Video update schema."""
    title: Optional[str] = None
    description: Optional[str] = None
    security_level: Optional[SecurityLevel] = None
    video_metadata: Optional[Dict[str, Any]] = None


class VideoResponse(VideoBase):
    """Video response schema."""
    id: UUID4
    organization_id: UUID4
    uploaded_by: UUID4
    status: VideoStatus
    duration: Optional[float]
    video_metadata: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class VideoSegmentResponse(BaseModel):
    """Video segment response schema."""
    id: UUID4
    video_id: UUID4
    segment_id: int
    start_time: float
    end_time: float
    text: str
    
    class Config:
        from_attributes = True


class SearchResult(BaseModel):
    """Search result schema."""
    video: VideoResponse
    segment: VideoSegmentResponse
    score: float
    url: str


class SearchRequest(BaseModel):
    """Search request schema."""
    query: str
    top_k: int = Field(default=5, ge=1, le=50)
    security_level_filter: Optional[List[SecurityLevel]] = None

