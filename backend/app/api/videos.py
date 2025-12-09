"""Video management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pathlib import Path
import uuid as uuid_lib
import shutil
import os
from app.database import get_db
from app.schemas.video import VideoResponse, VideoUpdate, VideoSegmentResponse
from app.models.video import Video, VideoSegment
from app.models.user import User
from app.models.enums import VideoStatus, SecurityLevel
from app.dependencies import get_current_active_user, get_current_user_optional
from app.services.access_control import can_access_video, can_edit_video, filter_accessible_videos
from app.config import get_settings
from app.tasks.video_tasks import transcribe_video_task

router = APIRouter()
settings = get_settings()


@router.post("/upload", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
async def upload_video(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    security_level: SecurityLevel = Form(SecurityLevel.INTERNAL),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload a video file."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization"
        )
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a video"
        )
    
    # Generate unique filename
    file_extension = Path(file.filename or "video.mp4").suffix
    video_id = uuid_lib.uuid4()
    filename = f"{video_id}{file_extension}"
    
    # Create organization directory if it doesn't exist
    org_dir = Path(settings.video_storage_path) / str(current_user.organization_id)
    org_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = org_dir / filename
    
    # Save file
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
    
    # Create video record
    video = Video(
        id=video_id,
        title=title,
        description=description,
        file_path=str(file_path),
        organization_id=current_user.organization_id,
        uploaded_by=current_user.id,
        security_level=security_level,
        status=VideoStatus.PROCESSING
    )
    
    db.add(video)
    db.commit()
    db.refresh(video)
    
    # Trigger async transcription task
    transcribe_video_task.delay(str(video.id))
    
    return video


@router.get("/", response_model=List[VideoResponse])
async def list_videos(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """List videos accessible to the current user."""
    # Get videos from user's organization
    if current_user.organization_id:
        videos = db.query(Video).filter(
            Video.organization_id == current_user.organization_id
        ).offset(skip).limit(limit).all()
    else:
        # Super admin without org can see all
        videos = db.query(Video).offset(skip).limit(limit).all()
    
    # Filter based on access control
    accessible_videos = filter_accessible_videos(current_user, videos, db)
    
    return accessible_videos


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: uuid_lib.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get video by ID."""
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    if not can_access_video(current_user, video, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return video


@router.get("/{video_id}/segments", response_model=List[VideoSegmentResponse])
async def get_video_segments(
    video_id: uuid_lib.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get video segments with transcriptions."""
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    if not can_access_video(current_user, video, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    segments = db.query(VideoSegment).filter(
        VideoSegment.video_id == video_id
    ).order_by(VideoSegment.segment_id).all()
    
    return segments


@router.patch("/{video_id}", response_model=VideoResponse)
async def update_video(
    video_id: uuid_lib.UUID,
    video_update: VideoUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update video metadata."""
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    if not can_edit_video(current_user, video, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Edit permission denied"
        )
    
    # Update fields
    if video_update.title is not None:
        video.title = video_update.title
    if video_update.description is not None:
        video.description = video_update.description
    if video_update.security_level is not None:
        video.security_level = video_update.security_level
    if video_update.metadata is not None:
        video.metadata = video_update.metadata
    
    db.commit()
    db.refresh(video)
    
    return video


@router.post("/{video_id}/reprocess", response_model=VideoResponse)
async def reprocess_video(
    video_id: uuid_lib.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Restart processing for a video (useful if processing failed or got stuck)."""
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    if not can_edit_video(current_user, video, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Edit permission denied"
        )
    
    # Check if video file still exists
    file_path = Path(video.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video file not found on disk"
        )
    
    # Delete existing segments to avoid duplicates
    db.query(VideoSegment).filter(VideoSegment.video_id == video_id).delete()
    
    # Reset video status to processing
    video.status = VideoStatus.PROCESSING
    video.duration = None
    db.commit()
    db.refresh(video)
    
    # Trigger async transcription task
    transcribe_video_task.delay(str(video.id))
    
    return video


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(
    video_id: uuid_lib.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a video."""
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    if not can_edit_video(current_user, video, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Delete permission denied"
        )
    
    # Delete file
    try:
        file_path = Path(video.file_path)
        if file_path.exists():
            file_path.unlink()
    except Exception:
        pass  # Continue even if file deletion fails
    
    db.delete(video)
    db.commit()
    
    return None


@router.get("/{video_id}/stream")
async def stream_video(
    video_id: uuid_lib.UUID,
    request: Request,
    db: Session = Depends(get_db),
    token: Optional[str] = None
):
    """Stream video file with HTTP range support for seeking.
    
    Accepts authentication via:
    - Authorization header (Bearer token) - preferred
    - Query parameter 'token' - for video elements that can't send headers
    """
    from fastapi import Query
    from app.services.auth import decode_access_token
    
    # Get user from token (header or query param)
    current_user = None
    auth_header = request.headers.get("Authorization")
    auth_token = None
    
    if auth_header and auth_header.startswith("Bearer "):
        auth_token = auth_header.split(" ")[1]
    elif token:
        auth_token = token
    
    if auth_token:
        try:
            payload = decode_access_token(auth_token)
            user_id = payload.get("sub")
            if user_id:
                current_user = db.query(User).filter(User.id == uuid_lib.UUID(user_id)).first()
        except Exception:
            pass
    
    if not current_user or not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    if not can_access_video(current_user, video, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    file_path = Path(video.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video file not found"
        )
    
    # Get file size and MIME type
    file_size = file_path.stat().st_size
    
    # Determine MIME type based on extension
    extension = file_path.suffix.lower()
    mime_types = {
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".ogg": "video/ogg",
        ".mov": "video/quicktime",
        ".avi": "video/x-msvideo",
        ".mkv": "video/x-matroska",
    }
    content_type = mime_types.get(extension, "video/mp4")
    
    # Handle range requests for video seeking
    range_header = request.headers.get("range")
    
    if range_header:
        # Parse range header (e.g., "bytes=0-1023")
        byte_range = range_header.replace("bytes=", "").split("-")
        start = int(byte_range[0]) if byte_range[0] else 0
        end = int(byte_range[1]) if len(byte_range) > 1 and byte_range[1] else file_size - 1
        end = min(end, file_size - 1)
        
        chunk_size = end - start + 1
        
        def file_chunk_generator():
            with open(file_path, "rb") as video_file:
                video_file.seek(start)
                remaining = chunk_size
                while remaining > 0:
                    chunk = video_file.read(min(8192, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk
        
        return StreamingResponse(
            file_chunk_generator(),
            status_code=206,  # Partial Content
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(chunk_size),
                "Content-Type": content_type,
            }
        )
    
    # No range request, return full file
    return FileResponse(
        file_path,
        media_type=content_type,
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
        }
    )

