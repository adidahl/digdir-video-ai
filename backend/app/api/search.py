"""Search endpoints using LightRAG knowledge graph."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import re
from app.database import get_db
from app.schemas.video import SearchRequest, SearchResult, VideoResponse, VideoSegmentResponse
from app.models.user import User
from app.models.video import Video, VideoSegment
from app.dependencies import get_current_active_user
from app.services.lightrag_service import get_lightrag_service
from app.services.access_control import can_access_video
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=List[SearchResult])
async def search_videos(
    search_request: SearchRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Search videos using LightRAG with knowledge graph + vector retrieval.
    
    LightRAG uses "mix" mode which combines:
    - Knowledge graph entities and relationships
    - Vector similarity search on chunks
    - Intelligent entity extraction
    
    This replaces the previous pgvector-only search with a more powerful system.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization"
        )
    
    try:
        # Get LightRAG service
        lightrag_service = await get_lightrag_service()
        
        # Query using LightRAG with "mix" mode (knowledge graph + vector)
        # Request only context (not LLM-generated answer) so we can parse metadata
        lightrag_context = await lightrag_service.search_async(
            organization_id=str(current_user.organization_id),
            query=search_request.query,
            mode="mix",
            top_k=search_request.top_k,
            only_need_context=True
        )
        
        # Parse LightRAG context to extract video segments
        # Context format includes headers like: [video_id=X;start=Y;end=Z;segment_id=N]
        search_results = []
        seen_segments = set()  # Avoid duplicates
        
        # Extract metadata headers from LightRAG context
        # Pattern: [video_id=<uuid>;start=<float>;end=<float>;segment_id=<int>]
        pattern = r'\[video_id=([^;]+);start=([^;]+);end=([^;]+);segment_id=([^\]]+)\]'
        matches = re.findall(pattern, lightrag_context)
        
        for match in matches:
            video_id_str, start_str, end_str, segment_id_str = match
            
            # Create unique key to avoid duplicates
            segment_key = (video_id_str, float(start_str))
            if segment_key in seen_segments:
                continue
            seen_segments.add(segment_key)
            
            try:
                # Fetch the actual video and segment from database
                video = db.query(Video).filter(
                    Video.id == video_id_str,
                    Video.organization_id == current_user.organization_id
                ).first()
                
                if not video:
                    continue
                
                # Check access control
                if not can_access_video(current_user, video, db):
                    continue
                
                # Filter by security level if specified
                if search_request.security_level_filter:
                    if video.security_level not in search_request.security_level_filter:
                        continue
                
                # Fetch the segment
                segment = db.query(VideoSegment).filter(
                    VideoSegment.video_id == video_id_str,
                    VideoSegment.start_time == float(start_str)
                ).first()
                
                if not segment:
                    continue
                
                # Build result URL
                url = f"/videos/{video.id}?t={int(segment.start_time)}"
                
                # Calculate relevance score (approximation based on order in context)
                # Earlier matches in context are more relevant
                score = 1.0 - (len(search_results) * 0.1)
                score = max(score, 0.1)  # Minimum score of 0.1
                
                search_results.append(SearchResult(
                    video=VideoResponse.from_orm(video),
                    segment=VideoSegmentResponse.from_orm(segment),
                    score=score,
                    url=url
                ))
                
            except Exception as e:
                logger.error(f"Error processing search result: {e}")
                continue
        
        logger.info(f"LightRAG search returned {len(search_results)} results for query: {search_request.query}")
        return search_results
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/lightrag/{query}")
async def search_with_lightrag_answer(
    query: str,
    current_user: User = Depends(get_current_active_user),
    mode: str = "mix",
    top_k: int = 5
):
    """Search using LightRAG and get an LLM-generated answer.
    
    This endpoint returns a natural language answer generated by LightRAG's LLM,
    based on the knowledge graph and retrieved context.
    
    Modes:
    - mix: Knowledge graph + vector retrieval (recommended)
    - hybrid: Combines local entities + global communities
    - local: Entity-focused retrieval
    - global: High-level community summaries
    - naive: Simple vector search on chunks
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization"
        )
    
    try:
        lightrag_service = await get_lightrag_service()
        
        # Query with LLM generation enabled
        result = await lightrag_service.search_async(
            organization_id=str(current_user.organization_id),
            query=query,
            mode=mode,
            top_k=top_k,
            only_need_context=False  # Get LLM-generated answer
        )
        
        return {
            "query": query,
            "answer": result,
            "mode": mode,
            "organization_id": str(current_user.organization_id)
        }
        
    except Exception as e:
        logger.error(f"LightRAG answer generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )
