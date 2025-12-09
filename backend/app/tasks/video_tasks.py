"""Video processing tasks."""
import whisper
import torch
import json
from pathlib import Path
from typing import List, Dict, Any
import uuid
import numpy as np
from sqlalchemy.orm import Session
from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models.video import Video, VideoSegment
from app.models.enums import VideoStatus
from app.config import get_settings
from app.services.video_processor import VideoProcessor

settings = get_settings()


@celery_app.task(bind=True, name="transcribe_video")
def transcribe_video_task(self, video_id: str):
    """Transcribe video using Whisper and process with LightRAG."""
    db = SessionLocal()
    
    try:
        # Get video from database
        video = db.query(Video).filter(Video.id == uuid.UUID(video_id)).first()
        if not video:
            raise ValueError(f"Video not found: {video_id}")
        
        # Update status
        video.status = VideoStatus.PROCESSING
        db.commit()
        
        # Load Whisper model
        print(f"Loading Whisper model: {settings.whisper_model}")
        device = settings.whisper_device
        if device == "cuda" and not torch.cuda.is_available():
            device = "cpu"
        
        model = whisper.load_model(settings.whisper_model, device=device)
        
        # Transcribe video
        print(f"Transcribing video: {video.file_path}")
        result = model.transcribe(
            video.file_path,
            language=None,  # Auto-detect
            verbose=False,
            word_timestamps=False
        )
        
        # Get video duration
        if "duration" in result:
            video.duration = result["duration"]
        
        # Save segments to database
        segments = result.get("segments", [])
        print(f"Processing {len(segments)} segments with LightRAG")
        
        # Process video with VideoProcessor
        # This will:
        # 1. Save segments to PostgreSQL
        # 2. Process with LightRAG for entity extraction and knowledge graph
        # 3. Store graph structure in Neo4j
        processor = VideoProcessor(db)
        video_segments = processor.process_video_segments(
            video,
            segments,
            result.get("text", "")
        )
        
        print(f"LightRAG processing completed for video {video_id}")
        
        # Update status
        video.status = VideoStatus.COMPLETED
        db.commit()
        
        print(f"Video transcription completed: {video_id}")
        
        return {
            "video_id": video_id,
            "status": "completed",
            "segments_count": len(segments),
            "duration": video.duration
        }
        
    except Exception as e:
        print(f"Error transcribing video {video_id}: {str(e)}")
        
        # Update status to failed
        if video:
            video.status = VideoStatus.FAILED
            db.commit()
        
        raise
    
    finally:
        db.close()

