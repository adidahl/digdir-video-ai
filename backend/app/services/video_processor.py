"""Video processing service for handling transcriptions and LightRAG integration."""
from pathlib import Path
from typing import List, Dict, Any
import asyncio
from sqlalchemy.orm import Session
from app.models.video import Video, VideoSegment
from app.services.lightrag_service import get_lightrag_service
from app.services.neo4j_service import Neo4jService
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class VideoProcessor:
    """Process video transcriptions and integrate with LightRAG."""
    
    def __init__(self, db: Session):
        self.db = db
        self.neo4j_service = Neo4jService()
    
    async def process_video_segments_async(
        self,
        video: Video,
        segments: List[Dict[str, Any]],
        full_transcript: str
    ):
        """Process video segments and store in databases.
        
        This method:
        1. Saves segments to PostgreSQL (without embeddings - LightRAG handles this)
        2. Processes with LightRAG for entity extraction and knowledge graph
        3. Stores basic graph structure in Neo4j
        
        LightRAG automatically:
        - Extracts entities and relationships using LLM
        - Generates embeddings for chunks, entities, and relationships
        - Stores everything in PostgreSQL + Neo4j backends
        """
        # Save segments to PostgreSQL without embeddings
        # LightRAG will handle embeddings and vector storage internally
        video_segments = []
        
        for seg in segments:
            segment_text = seg.get("text", "").strip()
            if not segment_text:
                continue
            
            # Create segment record without embedding
            # Note: embedding column will be NULL - LightRAG manages vectors separately
            video_segment = VideoSegment(
                video_id=video.id,
                segment_id=seg.get("id", 0),
                start_time=seg.get("start", 0.0),
                end_time=seg.get("end", 0.0),
                text=segment_text,
                embedding=None  # LightRAG handles embeddings internally
            )
            
            self.db.add(video_segment)
            video_segments.append(video_segment)
        
        self.db.commit()
        logger.info(f"Saved {len(video_segments)} segments to PostgreSQL for video {video.id}")
        
        # Process with LightRAG (organization-specific)
        # This is where the magic happens - entity extraction, knowledge graph, embeddings
        if video.organization_id:
            try:
                lightrag_service = await get_lightrag_service()
                await lightrag_service.process_video_transcript_async(
                    organization_id=str(video.organization_id),
                    video_id=str(video.id),
                    transcript=full_transcript,
                    segments=segments
                )
                logger.info(f"Processed video {video.id} with LightRAG")
            except Exception as e:
                logger.error(f"LightRAG processing failed for video {video.id}: {e}")
                # Don't fail the entire processing if LightRAG fails
                # The segments are still saved in PostgreSQL
        
        # Store basic graph structure in Neo4j
        # This is supplementary to LightRAG's knowledge graph
        try:
            self.neo4j_service.create_video_graph(
                video=video,
                segments=video_segments
            )
            logger.info(f"Created Neo4j graph for video {video.id}")
        except Exception as e:
            logger.error(f"Neo4j graph creation failed for video {video.id}: {e}")
        
        return video_segments
    
    def process_video_segments(
        self,
        video: Video,
        segments: List[Dict[str, Any]],
        full_transcript: str
    ):
        """Synchronous wrapper for async processing.
        
        This is used by Celery tasks which may not support async directly.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.process_video_segments_async(video, segments, full_transcript)
            )
        finally:
            # Wait for all pending tasks to complete before closing
            pending = asyncio.all_tasks(loop)
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.close()
