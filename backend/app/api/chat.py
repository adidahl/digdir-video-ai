"""Chat API endpoints with conversational memory."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import re
import uuid
from app.database import get_db
from app.schemas.conversation import (
    ChatRequest, ChatResponse, ConversationResponse,
    ConversationWithMessages, MessageSource, DebugSourcesRequest
)
from app.models.user import User
from app.models.video import Video, VideoSegment
from app.dependencies import get_current_active_user
from app.services.conversation_service import ConversationService
from app.services.lightrag_service import get_lightrag_service
from app.services.access_control import can_access_video
from lightrag import QueryParam
from lightrag.llm.openai import gpt_4o_mini_complete
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/message", response_model=ChatResponse)
async def send_message(
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Send a chat message with optional conversation context."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization"
        )
    
    conversation_service = ConversationService(db)
    
    # Get or create conversation
    if chat_request.conversation_id:
        conversation = conversation_service.get_conversation(
            chat_request.conversation_id,
            current_user
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
    else:
        # Create new conversation with auto-title from first message
        title = chat_request.message[:50] + "..." if len(chat_request.message) > 50 else chat_request.message
        conversation = conversation_service.create_conversation(current_user, title=title)
    
    # Add user message
    user_message = conversation_service.add_message(
        conversation,
        role="user",
        content=chat_request.message
    )
    
    # Get conversation history for LightRAG context
    history = conversation_service.get_conversation_history_for_lightrag(
        conversation.id,
        current_user,
        max_messages=10  # Include last 10 messages for context
    )
    
    # Remove the current message from history (it's already in the query)
    if history:
        history = history[:-1]
    
    try:
        # Get LightRAG service
        lightrag_service = await get_lightrag_service()
        
        # Custom prompt for conversational responses
        custom_prompt = """
You are a helpful video search assistant. When answering questions:
1. Provide a natural, conversational response
2. Reference specific videos where information was found
3. Mention timestamps when relevant
4. Be concise but informative
5. If the user asks a follow-up question, use the conversation context
6. If information spans multiple videos, mention all relevant sources
"""
        
        # Query LightRAG with conversation history (memory!)
        # Strategy: Use vector-only mode for source extraction (more accurate metadata headers)
        # and mix mode for the actual answer (better answer quality with knowledge graph)
        
        # First, get sources using vector-only mode (preserves metadata headers better)
        logger.info("Fetching sources using vector-only mode for accurate metadata headers...")
        lightrag_context_vectors = await lightrag_service.search_async(
            organization_id=str(current_user.organization_id),
            query=chat_request.message,
            mode="naive",  # Vector-only mode - preserves exact segment metadata
            top_k=10,  # Get more results for better source extraction
            conversation_history=None,  # Don't use history for source extraction
            only_need_context=True,  # Get context with metadata headers
            user_prompt=None
        )
        
        # Also get context from mix mode as backup
        logger.info("Fetching context using mix mode for comprehensive retrieval...")
        lightrag_context_mix = await lightrag_service.search_async(
            organization_id=str(current_user.organization_id),
            query=chat_request.message,
            mode="mix",  # Knowledge graph + vector retrieval
            top_k=10,
            conversation_history=history,
            only_need_context=True,
            user_prompt=None
        )
        
        # Combine both contexts for source extraction (prioritize vector mode headers)
        # Vector mode should have more accurate metadata headers
        combined_context = lightrag_context_vectors + "\n\n" + lightrag_context_mix
        
        logger.info(f"Vector mode context length: {len(lightrag_context_vectors)}")
        logger.info(f"Mix mode context length: {len(lightrag_context_mix)}")
        logger.debug(f"Vector context preview: {lightrag_context_vectors[:500]}")
        logger.debug(f"Mix context preview: {lightrag_context_mix[:500]}")
        
        # Log full contexts for debugging (first 2000 chars each)
        logger.debug(f"Full vector context (first 2000 chars):\n{lightrag_context_vectors[:2000]}")
        logger.debug(f"Full mix context (first 2000 chars):\n{lightrag_context_mix[:2000]}")
        
        # Parse sources from combined context (prioritize vector mode results)
        sources = await _parse_sources_from_lightrag(
            combined_context,
            chat_request.message,  # Pass query for validation
            current_user,
            db
        )
        
        logger.info(f"Parsed {len(sources)} sources from context")
        
        # Now get the LLM-generated answer
        lightrag_answer = await lightrag_service.search_async(
            organization_id=str(current_user.organization_id),
            query=chat_request.message,
            mode="mix",  # Knowledge graph + vector retrieval
            top_k=5,
            conversation_history=history,  # <-- This enables memory!
            only_need_context=False,  # Get LLM-generated answer
            user_prompt=custom_prompt  # Custom instructions for conversational responses
        )
        
        logger.info(f"Generated answer length: {len(lightrag_answer)}")
        logger.debug(f"Answer preview: {lightrag_answer[:500]}")
        
        # Post-process answer to fix transcription errors using context from sources
        # This will be done after we have sources, so we can use their context
        # But we'll prepare the function call here
        
        # Improve sources by searching based on answer content
        # Extract entities and key terms from the answer to find relevant segments
        answer_based_sources = await _search_sources_from_answer(
            lightrag_answer,
            chat_request.message,
            current_user,
            db
        )
        
        # Combine and prioritize sources
        # Priority: 1) Answer-based sources (most relevant), 2) LightRAG context sources
        if len(answer_based_sources) > 0:
            logger.info(f"Found {len(answer_based_sources)} sources from answer-based search")
            # Merge sources, avoiding duplicates, prioritizing answer-based ones
            seen_keys = set()
            combined_sources = []
            
            # Add answer-based sources first (higher priority)
            for source in answer_based_sources:
                key = (source.video_id, int(source.timestamp))
                if key not in seen_keys:
                    combined_sources.append(source)
                    seen_keys.add(key)
            
            # Add LightRAG context sources if not duplicate
            for source in sources:
                key = (source.video_id, int(source.timestamp))
                if key not in seen_keys:
                    combined_sources.append(source)
                    seen_keys.add(key)
            
            sources = combined_sources  # No limit - we'll filter by relevance later
            logger.info(f"Combined {len(combined_sources)} total sources (prioritizing answer-based)")
        
        elif len(sources) == 0:
            logger.warning("No sources found from LightRAG context or answer, using fallback search")
            sources = await _search_videos_by_query(
                chat_request.message,
                current_user,
                db
            )
            logger.info(f"Found {len(sources)} sources from database fallback search")
        else:
            # Validate existing sources - check if they contain answer entities
            answer_lower = lightrag_answer.lower()
            
            # Extract entities from answer (person names, locations, job titles, etc.)
            answer_entities = re.findall(r'\b[A-ZÆØÅ][a-zæøå]+(?:\s+[A-ZÆØÅ][a-zæøå]+)*\b', lightrag_answer)
            # Also extract key terms (words that appear in answer but not common words)
            answer_keywords = [word.lower() for word in lightrag_answer.split() 
                             if len(word) > 3 and word.lower() not in ['som', 'det', 'er', 'og', 'har', 'kan', 'for', 'med', 'den', 'til', 'der', 'sitt', 'sin', 'sine']]
            
            # Check relevance of existing sources
            relevant_source_count = 0
            for source in sources:
                source_text_lower = source.text.lower()
                # Check if source contains any answer entities or key terms
                has_entity = any(entity.lower() in source_text_lower for entity in answer_entities)
                has_keyword = sum(1 for keyword in answer_keywords if keyword in source_text_lower) >= 2
                
                if has_entity or has_keyword:
                    relevant_source_count += 1
            
            logger.info(f"Found {relevant_source_count}/{len(sources)} sources relevant to answer content")
            
            # If sources aren't relevant enough, use answer-based search
            if relevant_source_count < len(sources) / 2 and (len(answer_entities) > 0 or len(answer_keywords) > 0):
                logger.warning(
                    f"Sources from LightRAG context don't seem relevant to answer. "
                    f"Trying answer-based search..."
                )
                answer_based_sources = await _search_sources_from_answer(
                    lightrag_answer,
                    chat_request.message,
                    current_user,
                    db
                )
                if len(answer_based_sources) > 0:
                    logger.info(f"Using {len(answer_based_sources)} sources from answer-based search instead")
                    sources = answer_based_sources
        
        # Filter sources to only include relevant ones
        sources = await _filter_relevant_sources(
            sources,
            lightrag_answer,
            chat_request.message
        )
        
        logger.info(f"After filtering, {len(sources)} relevant sources remain")
        
        # Add context (surrounding segments) to sources for better post-processing
        # Only if we have relevant sources
        if sources:
            sources = await _add_context_to_sources(sources, current_user, db)
        
        # Post-process answer to fix transcription errors and improve accuracy
        # Only if we have relevant sources with context
        if sources:
            lightrag_answer = await _post_process_answer_with_context(
                lightrag_answer,
                sources,
                chat_request.message
            )
            logger.info("Post-processed answer to fix transcription errors")
        
        # Store assistant response with sources (may be empty list if no relevant sources)
        assistant_message = conversation_service.add_message(
            conversation,
            role="assistant",
            content=lightrag_answer,
            sources=[s.dict() for s in sources]
        )
        
        return ChatResponse(
            conversation_id=conversation.id,
            message_id=assistant_message.id,
            answer=lightrag_answer,
            sources=sources,
            created_at=assistant_message.created_at
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat failed: {str(e)}"
        )


@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50
):
    """List user's conversations."""
    conversation_service = ConversationService(db)
    conversations = conversation_service.list_conversations(current_user, skip, limit)
    
    # Add message count
    results = []
    for conv in conversations:
        conv_dict = {
            "id": conv.id,
            "user_id": conv.user_id,
            "organization_id": conv.organization_id,
            "title": conv.title,
            "created_at": conv.created_at,
            "updated_at": conv.updated_at,
            "message_count": len(conv.messages)
        }
        results.append(ConversationResponse(**conv_dict))
    
    return results


@router.get("/{conversation_id}/messages", response_model=ConversationWithMessages)
async def get_conversation_messages(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a conversation with all its messages."""
    conversation_service = ConversationService(db)
    conversation = conversation_service.get_conversation(conversation_id, current_user)
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    return conversation


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a conversation."""
    conversation_service = ConversationService(db)
    success = conversation_service.delete_conversation(conversation_id, current_user)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    return None


@router.post("/debug/sources", response_model=Dict[str, Any])
async def debug_source_extraction(
    request: DebugSourcesRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Debug endpoint to inspect source extraction for a query.
    
    Returns detailed information about:
    - Raw LightRAG context (vector and mix modes)
    - Extracted metadata headers
    - Database segment matches
    - Source validation results
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization"
        )
    
    try:
        query = request.query
        lightrag_service = await get_lightrag_service()
        
        # Get contexts from both modes
        vector_context = await lightrag_service.search_async(
            organization_id=str(current_user.organization_id),
            query=query,
            mode="naive",
            top_k=10,
            only_need_context=True,
            conversation_history=None,
            user_prompt=None
        )
        
        mix_context = await lightrag_service.search_async(
            organization_id=str(current_user.organization_id),
            query=query,
            mode="mix",
            top_k=10,
            only_need_context=True,
            conversation_history=None,
            user_prompt=None
        )
        
        # Extract metadata headers
        # UUID pattern: 8-4-4-4-12 hex characters
        # Use word boundaries or non-word characters to ensure we only match complete UUIDs
        uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        pattern = rf'\[video_id=({uuid_pattern});start=([^;]+);end=([^;]+);segment_id=([^\]]+)\]'
        vector_headers = re.findall(pattern, vector_context, re.IGNORECASE)
        mix_headers = re.findall(pattern, mix_context, re.IGNORECASE)
        
        logger.info(f"Extracted {len(vector_headers)} vector headers and {len(mix_headers)} mix headers")
        if vector_headers:
            logger.debug(f"Sample vector header: {vector_headers[0]}")
        if mix_headers:
            logger.debug(f"Sample mix header: {mix_headers[0]}")
        
        # Get answer
        answer = await lightrag_service.search_async(
            organization_id=str(current_user.organization_id),
            query=query,
            mode="mix",
            top_k=5,
            only_need_context=False,
            conversation_history=None,
            user_prompt=None
        )
        
        # Parse sources from context
        combined_context = vector_context + "\n\n" + mix_context
        context_sources = await _parse_sources_from_lightrag(
            combined_context,
            query,
            current_user,
            db
        )
        
        # Also try answer-based search
        answer_based_sources = await _search_sources_from_answer(
            answer,
            query,
            current_user,
            db
        )
        
        # Combine sources (avoid duplicates)
        seen_keys = set()
        sources = []
        for source in answer_based_sources:
            key = (source.video_id, int(source.timestamp))
            if key not in seen_keys:
                sources.append(source)
                seen_keys.add(key)
        for source in context_sources:
            key = (source.video_id, int(source.timestamp))
            if key not in seen_keys:
                sources.append(source)
                seen_keys.add(key)
        sources = sources[:5]  # Limit to 5
        
        # Validate segments in database
        segment_validations = []
        for header_set_name, headers in [("vector", vector_headers), ("mix", mix_headers)]:
            for video_id_str, start_str, end_str, segment_id_str in headers:
                try:
                    # Clean and validate video_id
                    video_id_str = video_id_str.strip()
                    
                    # Validate it looks like a UUID
                    if not re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', video_id_str, re.IGNORECASE):
                        logger.warning(f"Invalid video_id format in {header_set_name} header: {video_id_str[:50]}")
                        segment_validations.append({
                            "mode": header_set_name,
                            "video_id": video_id_str,
                            "header_start": float(start_str) if start_str else None,
                            "header_segment_id": segment_id_str,
                            "found": False,
                            "actual_start": None,
                            "actual_segment_id": None,
                            "segment_text": None,
                            "matches_header": False,
                            "error": "Invalid UUID format"
                        })
                        continue
                    
                    start_time = float(start_str)
                    segment = db.query(VideoSegment).filter(
                        VideoSegment.video_id == video_id_str,
                        VideoSegment.start_time >= start_time - 0.1,
                        VideoSegment.start_time <= start_time + 0.1
                    ).first()
                    
                    segment_validations.append({
                        "mode": header_set_name,
                        "video_id": video_id_str,
                        "header_start": start_time,
                        "header_segment_id": segment_id_str,
                        "found": segment is not None,
                        "actual_start": segment.start_time if segment else None,
                        "actual_segment_id": segment.segment_id if segment else None,
                        "segment_text": segment.text[:200] if segment else None,
                        "matches_header": segment and abs(segment.start_time - start_time) < 0.1
                    })
                except (ValueError, Exception) as e:
                    logger.error(f"Error validating segment in {header_set_name} mode: {e}")
                    segment_validations.append({
                        "mode": header_set_name,
                        "video_id": video_id_str[:50] if video_id_str else "invalid",
                        "header_start": None,
                        "header_segment_id": segment_id_str,
                        "found": False,
                        "actual_start": None,
                        "actual_segment_id": None,
                        "segment_text": None,
                        "matches_header": False,
                        "error": str(e)
                    })
        
        return {
            "query": query,
            "answer": answer,
            "vector_context_preview": vector_context[:1000],
            "mix_context_preview": mix_context[:1000],
            "vector_headers_count": len(vector_headers),
            "mix_headers_count": len(mix_headers),
            "vector_headers": vector_headers[:10],  # First 10
            "mix_headers": mix_headers[:10],  # First 10
            "segment_validations": segment_validations[:20],  # First 20
            "parsed_sources": [s.dict() for s in sources],
            "sources_count": len(sources)
        }
        
    except Exception as e:
        logger.error(f"Debug source extraction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Debug failed: {str(e)}"
        )


async def _parse_sources_from_lightrag(
    lightrag_response: str,
    query: str,
    current_user: User,
    db: Session
) -> List[MessageSource]:
    """Parse video sources from LightRAG response context.
    
    LightRAG context contains metadata headers like:
    [video_id=X;start=Y;end=Z;segment_id=N] followed by text content
    
    This function also validates that the segments actually contain relevant content
    to ensure source accuracy.
    """
    sources = []
    seen = set()
    
    # Extract metadata headers: [video_id=X;start=Y;end=Z;segment_id=N]
    # Use UUID pattern to ensure we only match valid video IDs
    uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    pattern = rf'\[video_id=({uuid_pattern});start=([^;]+);end=([^;]+);segment_id=([^\]]+)\]'
    matches = re.findall(pattern, lightrag_response, re.IGNORECASE)
    
    logger.info(f"Found {len(matches)} metadata headers in LightRAG response")
    logger.debug(f"Query: {query}")
    
    # Extract context text after each header to validate relevance
    # Split by headers and extract text following each header
    header_text_pairs = []
    parts = re.split(r'(\[video_id=[^\]]+\])', lightrag_response)
    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            header = parts[i]
            text_after = parts[i + 1][:500] if len(parts[i + 1]) > 500 else parts[i + 1]  # First 500 chars
            header_text_pairs.append((header, text_after))
    
    # Extract query keywords for relevance validation
    query_keywords = [word.lower() for word in query.split() if len(word) > 2]
    
    for match_idx, match in enumerate(matches):
        video_id_str, start_str, end_str, segment_id_str = match
        
        # Clean and validate video_id
        video_id_str = video_id_str.strip()
        
        # Validate UUID format before using it
        if not re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', video_id_str, re.IGNORECASE):
            logger.warning(f"Invalid video_id format in header: {video_id_str[:50]}... (skipping)")
            continue
        
        # Validate start_time before creating key
        try:
            start_time = float(start_str)
        except ValueError:
            logger.warning(f"Invalid start_time in header: {start_str} (skipping)")
            continue
        
        # Avoid duplicates
        key = (video_id_str, start_time)
        if key in seen:
            logger.debug(f"Skipping duplicate header: {key}")
            continue
        seen.add(key)
        
        try:
            # Fetch video
            video = db.query(Video).filter(
                Video.id == video_id_str,
                Video.organization_id == current_user.organization_id
            ).first()
            
            if not video or not can_access_video(current_user, video, db):
                logger.warning(f"Video {video_id_str} not found or access denied")
                continue
            
            # Fetch segment - try to find by start_time (with some tolerance)
            # start_time is already validated above
            segment = db.query(VideoSegment).filter(
                VideoSegment.video_id == video_id_str,
                VideoSegment.start_time >= start_time - 0.1,
                VideoSegment.start_time <= start_time + 0.1
            ).first()
            
            if not segment:
                # Try matching by segment_id from metadata
                try:
                    segment_id_int = int(segment_id_str)
                    segment = db.query(VideoSegment).filter(
                        VideoSegment.video_id == video_id_str,
                        VideoSegment.segment_id == segment_id_int
                    ).first()
                    if segment:
                        logger.info(f"Matched segment by segment_id {segment_id_int} for video {video_id_str}")
                except ValueError:
                    pass
            
            if not segment:
                # If exact match fails, get any segment from this video
                segment = db.query(VideoSegment).filter(
                    VideoSegment.video_id == video_id_str
                ).first()
                if segment:
                    logger.warning(
                        f"Using approximate segment match for video {video_id_str}: "
                        f"header said {start_time}s, but using {segment.start_time}s"
                    )
            
            if not segment:
                logger.warning(f"No segment found for video {video_id_str} at {start_time}s (segment_id: {segment_id_str})")
                continue
            
            # Validate that segment actually contains relevant content
            segment_text_lower = segment.text.lower()
            context_text = ""
            if match_idx < len(header_text_pairs):
                context_text = header_text_pairs[match_idx][1].lower()
            
            # Check if segment text or context text contains query keywords
            has_relevant_content = False
            if query_keywords:
                # Check segment text
                segment_matches = sum(1 for keyword in query_keywords if keyword in segment_text_lower)
                # Check context text (what LightRAG thinks is relevant)
                context_matches = sum(1 for keyword in query_keywords if keyword in context_text)
                
                if segment_matches > 0 or context_matches > 0:
                    has_relevant_content = True
                    logger.debug(
                        f"Segment at {segment.start_time}s: {segment_matches} keyword matches in segment, "
                        f"{context_matches} in context"
                    )
            else:
                # If no keywords to check, assume relevant
                has_relevant_content = True
            
            if not has_relevant_content:
                logger.warning(
                    f"Segment at {segment.start_time}s doesn't contain query keywords. "
                    f"Segment text: {segment.text[:100]}... Skipping."
                )
                continue
            
            # Create source
            sources.append(MessageSource(
                video_id=str(video.id),
                video_title=video.title,
                timestamp=segment.start_time,
                text=segment.text[:200] + "..." if len(segment.text) > 200 else segment.text,
                url=f"/videos/{video.id}?t={int(segment.start_time)}"
            ))
            
            logger.info(
                f"Added validated source: {video.title} at {segment.start_time}s "
                f"(header: {start_time}s, segment_id: {segment.segment_id})"
            )
            
            # No hard limit - we'll filter by relevance later
            # Limit to reasonable number to avoid performance issues (e.g., 20 candidates)
            if len(sources) >= 20:
                break
                
        except Exception as e:
            logger.error(f"Error parsing source: {e}", exc_info=True)
            continue
    
    logger.info(f"Parsed {len(sources)} validated sources from LightRAG response")
    
    # If no sources found after validation, try fallback search
    if len(sources) == 0:
        logger.warning("No validated sources found. This may indicate metadata header mismatch.")
    
    return sources


async def _search_sources_from_answer(
    answer: str,
    query: str,
    current_user: User,
    db: Session,
    limit: int = 5
) -> List[MessageSource]:
    """Search for video segments based on entities and key terms from the answer.
    
    This function extracts entities (person names, locations, job titles, etc.)
    and key terms from the answer and searches the database for segments that
    contain them. This is more accurate than relying only on LightRAG context
    metadata headers.
    """
    from sqlalchemy import or_, and_
    
    sources = []
    
    # Extract entities from answer (capitalized words/phrases - likely names, places, titles)
    answer_entities = re.findall(r'\b[A-ZÆØÅ][a-zæøå]+(?:\s+[A-ZÆØÅ][a-zæøå]+)*\b', answer)
    
    # Extract key terms from answer (longer words that are meaningful)
    # Filter out common Norwegian stopwords
    stopwords = {'som', 'det', 'er', 'og', 'har', 'kan', 'for', 'med', 'den', 'til', 
                 'der', 'sitt', 'sin', 'sine', 'han', 'hun', 'de', 'som', 'en', 'et', 
                 'på', 'av', 'med', 'ved', 'om', 'i', 'jobb', 'arbeid'}
    answer_keywords = [word.lower() for word in answer.split() 
                      if len(word) > 3 and word.lower() not in stopwords]
    
    # Also extract terms from query if not in answer
    query_entities = re.findall(r'\b[A-ZÆØÅ][a-zæøå]+(?:\s+[A-ZÆØÅ][a-zæøå]+)*\b', query)
    query_keywords = [word.lower() for word in query.split() 
                     if len(word) > 3 and word.lower() not in stopwords]
    
    # Combine all search terms
    all_entities = list(set(answer_entities + query_entities))
    all_keywords = list(set(answer_keywords + query_keywords))[:10]  # Limit to 10 keywords
    
    logger.info(f"Searching for segments with entities: {all_entities[:5]} and keywords: {all_keywords[:5]}")
    
    if not all_entities and not all_keywords:
        return sources
    
    try:
        # Build search filter
        filters = []
        
        # Search for entities (exact match or partial match)
        if all_entities:
            for entity in all_entities[:5]:  # Limit to 5 entities
                filters.append(VideoSegment.text.ilike(f"%{entity}%"))
        
        # Search for keywords (at least 2 keywords should match)
        if all_keywords:
            # Use OR for keywords - segment should contain at least one
            keyword_filters = [VideoSegment.text.ilike(f"%{keyword}%") for keyword in all_keywords[:5]]
            if keyword_filters:
                filters.append(or_(*keyword_filters))
        
        if not filters:
            return sources
        
        # Combine with OR - segment should match at least one entity or keyword
        search_filter = or_(*filters)
        
        # Search segments
        segments = db.query(VideoSegment).join(Video).filter(
            Video.organization_id == current_user.organization_id,
            search_filter
        ).order_by(VideoSegment.start_time).limit(limit * 5).all()  # Get more, then filter
        
        # Score and prioritize segments
        scored_segments = []
        for segment in segments:
            score = 0
            segment_text_lower = segment.text.lower()
            
            # Score by entity matches (higher weight)
            for entity in all_entities:
                if entity.lower() in segment_text_lower:
                    score += 3  # Entities are more important
            
            # Score by keyword matches
            for keyword in all_keywords:
                if keyword in segment_text_lower:
                    score += 1
            
            # Bonus if segment contains multiple entities/keywords
            if score > 0:
                scored_segments.append((score, segment))
        
        # Sort by score (highest first) and take top results
        scored_segments.sort(key=lambda x: x[0], reverse=True)
        
        seen_videos_timestamps = set()
        for score, segment in scored_segments:
            key = (str(segment.video_id), int(segment.start_time))
            if key in seen_videos_timestamps:
                continue
            seen_videos_timestamps.add(key)
            
            video = segment.video
            if not can_access_video(current_user, video, db):
                continue
            
            sources.append(MessageSource(
                video_id=str(video.id),
                video_title=video.title,
                timestamp=segment.start_time,
                text=segment.text[:200] + "..." if len(segment.text) > 200 else segment.text,
                url=f"/videos/{video.id}?t={int(segment.start_time)}"
            ))
            
            # Get more candidates, filtering will happen later
            # Limit to reasonable number to avoid performance issues
            if len(sources) >= limit * 3:
                break
                
        logger.info(f"Found {len(sources)} candidate segments from answer-based search (will filter for relevance)")
        
    except Exception as e:
        logger.error(f"Error in answer-based source search: {e}", exc_info=True)
    
    return sources


async def _search_videos_by_query(
    query: str,
    current_user: User,
    db: Session,
    limit: int = 5
) -> List[MessageSource]:
    """Fallback: Search database for videos matching query terms."""
    from sqlalchemy import or_, func
    
    sources = []
    
    # Extract keywords from query (simple approach)
    keywords = query.lower().split()
    keywords = [k.strip() for k in keywords if len(k) > 2]  # Filter short words
    
    if not keywords:
        return sources
    
    try:
        # Search for videos with matching segments
        # This is a simple text search - in production you'd use full-text search
        query_filter = or_(
            *[VideoSegment.text.ilike(f"%{keyword}%") for keyword in keywords[:3]]  # Limit to 3 keywords
        )
        
        segments = db.query(VideoSegment).join(Video).filter(
            Video.organization_id == current_user.organization_id,
            query_filter
        ).limit(limit * 3).all()  # Get more segments, then deduplicate by video
        
        seen_videos = set()
        for segment in segments:
            if segment.video_id in seen_videos:
                continue
            seen_videos.add(segment.video_id)
            
            video = segment.video
            if not can_access_video(current_user, video, db):
                continue
            
            sources.append(MessageSource(
                video_id=str(video.id),
                video_title=video.title,
                timestamp=segment.start_time,
                text=segment.text[:200] + "..." if len(segment.text) > 200 else segment.text,
                url=f"/videos/{video.id}?t={int(segment.start_time)}"
            ))
            
            if len(sources) >= limit:
                break
                
    except Exception as e:
        logger.error(f"Error in fallback video search: {e}")
    
    return sources


async def _filter_relevant_sources(
    sources: List[MessageSource],
    answer: str,
    query: str
) -> List[MessageSource]:
    """Filter sources to only include those that are relevant to the answer and query.
    
    A source is considered relevant if:
    1. It contains entities mentioned in the answer or query
    2. It contains multiple key terms from the answer or query
    3. The answer mentions specific information that could come from that segment
    """
    if not sources:
        return []
    
    # If answer is just a greeting or generic response, no sources are relevant
    greetings = ['hi', 'hello', 'hej', 'hei', 'hey', 'hallo', 'hallo der', 'hei der', 'heisann']
    generic_responses = ['kan hjelpe', 'hjelpe deg', 'hjelpe deg med', 'assist', 'help you', 
                        'hva kan jeg hjelpe', 'hva kan jeg hjelpe deg', 'hva kan jeg hjelpe deg med',
                        'hvordan kan jeg', 'hvordan kan jeg hjelpe', 'how can i help']
    
    answer_lower = answer.lower().strip()
    query_lower = query.lower().strip()
    
    # Check if this is just a greeting/generic interaction
    is_greeting = any(greeting in answer_lower for greeting in greetings)
    is_generic = any(phrase in answer_lower for phrase in generic_responses)
    
    # Check if query is very short or generic
    query_words = query.split()
    is_short_query = len(query_words) <= 2
    is_generic_query = query_lower in ['hi', 'hello', 'hej', 'hei', 'hey', 'hallo', 'hola']
    
    # If it's just a greeting/generic response and query is short/generic, no sources needed
    if (is_greeting or is_generic) and (is_short_query or is_generic_query):
        logger.info(f"Detected greeting/generic interaction (query: '{query}', answer starts with greeting) - filtering out all sources")
        return []
    
    # Also check if answer is very short and doesn't contain specific information
    answer_words = answer.split()
    if len(answer_words) <= 5 and is_generic:
        logger.info("Answer is very short and generic - filtering out all sources")
        return []
    
    # Extract entities from answer and query
    answer_entities = re.findall(r'\b[A-ZÆØÅ][a-zæøå]+(?:\s+[A-ZÆØÅ][a-zæøå]+)*\b', answer)
    query_entities = re.findall(r'\b[A-ZÆØÅ][a-zæøå]+(?:\s+[A-ZÆØÅ][a-zæøå]+)*\b', query)
    all_entities = list(set(answer_entities + query_entities))
    
    # Extract meaningful keywords (filter stopwords)
    stopwords = {'som', 'det', 'er', 'og', 'har', 'kan', 'for', 'med', 'den', 'til', 
                 'der', 'sitt', 'sin', 'sine', 'han', 'hun', 'de', 'en', 'et', 
                 'på', 'av', 'ved', 'om', 'i', 'jobb', 'arbeid', 'hva', 'hvem', 
                 'hvor', 'hvorfor', 'hvordan', 'når', 'du', 'deg', 'din', 'ditt',
                 'meg', 'deg', 'seg', 'oss', 'dere', 'seg', 'jeg', 'vi', 'de'}
    
    answer_words = [w.lower() for w in answer.split() if len(w) > 3 and w.lower() not in stopwords]
    query_words = [w.lower() for w in query.split() if len(w) > 3 and w.lower() not in stopwords]
    
    # Combine keywords and remove duplicates
    all_keywords = list(set(answer_words + query_words))
    
    # If no meaningful entities or keywords, don't show sources
    # But be more lenient - if there are some keywords, allow sources with lower threshold
    if not all_entities and len(all_keywords) < 1:
        logger.info("No meaningful entities or keywords found - filtering out all sources")
        return []
    
    relevant_sources = []
    
    for source in sources:
        source_text_lower = source.text.lower()
        relevance_score = 0
        
        # Score by entity matches (high weight)
        entity_matches = sum(1 for entity in all_entities if entity.lower() in source_text_lower)
        if entity_matches > 0:
            relevance_score += entity_matches * 3
        
        # Score by keyword matches
        keyword_matches = sum(1 for keyword in all_keywords if keyword in source_text_lower)
        if keyword_matches >= 2:
            relevance_score += keyword_matches
        
        # Check if source text contains query terms (if query has meaningful content)
        if len(query.split()) > 3:  # Only if query has some substance
            query_term_matches = sum(1 for word in query.split() 
                                   if len(word) > 3 and word.lower() in source_text_lower)
            if query_term_matches >= 2:
                relevance_score += 2
        
        # Source is relevant if it has a minimum score
        # Entity match = definitely relevant
        # Multiple keyword matches = probably relevant
        if relevance_score >= 2:
            relevant_sources.append(source)
            logger.debug(f"Source at {source.timestamp}s is relevant (score: {relevance_score})")
        else:
            logger.debug(f"Source at {source.timestamp}s is not relevant (score: {relevance_score})")
    
    # Sort by relevance (if we have scores, could sort, but for now just return filtered)
    logger.info(f"Filtered {len(sources)} sources to {len(relevant_sources)} relevant ones")
    
    return relevant_sources


async def _add_context_to_sources(
    sources: List[MessageSource],
    current_user: User,
    db: Session,
    context_segments: int = 2
) -> List[MessageSource]:
    """Add surrounding segment context to sources for better understanding.
    
    For each source, retrieves the previous and next N segments to provide
    context that can help with transcription error correction.
    """
    from app.models.video import VideoSegment
    
    enhanced_sources = []
    
    for source in sources:
        try:
            # Find the segment
            segment = db.query(VideoSegment).filter(
                VideoSegment.video_id == source.video_id,
                VideoSegment.start_time >= source.timestamp - 0.5,
                VideoSegment.start_time <= source.timestamp + 0.5
            ).first()
            
            if not segment:
                # If exact match not found, get closest segment
                segment = db.query(VideoSegment).filter(
                    VideoSegment.video_id == source.video_id
                ).order_by(
                    (VideoSegment.start_time - source.timestamp).abs()
                ).first()
            
            if segment:
                # Get previous segments
                previous_segments = db.query(VideoSegment).filter(
                    VideoSegment.video_id == source.video_id,
                    VideoSegment.start_time < segment.start_time
                ).order_by(VideoSegment.start_time.desc()).limit(context_segments).all()
                
                # Get next segments
                next_segments = db.query(VideoSegment).filter(
                    VideoSegment.video_id == source.video_id,
                    VideoSegment.start_time > segment.start_time
                ).order_by(VideoSegment.start_time.asc()).limit(context_segments).all()
                
                # Build context text
                context_parts = []
                if previous_segments:
                    context_parts.append("...")
                    for prev_seg in reversed(previous_segments):
                        context_parts.append(prev_seg.text)
                
                context_parts.append(f"[MAIN SEGMENT: {segment.text}]")
                
                if next_segments:
                    for next_seg in next_segments:
                        context_parts.append(next_seg.text)
                    context_parts.append("...")
                
                # Create enhanced source with context
                # Keep original text for display, but add context info
                enhanced_source = MessageSource(
                    video_id=source.video_id,
                    video_title=source.video_title,
                    timestamp=source.timestamp,
                    text=" ".join(context_parts),  # Include context in text for post-processing
                    url=source.url
                )
                enhanced_sources.append(enhanced_source)
            else:
                # If segment not found, use original source
                enhanced_sources.append(source)
                
        except Exception as e:
            logger.error(f"Error adding context to source: {e}", exc_info=True)
            # On error, use original source
            enhanced_sources.append(source)
    
    return enhanced_sources


async def _post_process_answer_with_context(
    answer: str,
    sources: List[MessageSource],
    query: str
) -> str:
    """Post-process the answer to fix transcription errors using context from sources.
    
    Uses LLM to:
    1. Identify potential transcription errors in the answer
    2. Use context from source segments to correct them
    3. Ensure all words make sense in the context
    """
    try:
        # Build context from sources (use the enhanced context text we added)
        source_contexts = []
        for i, source in enumerate(sources[:3], 1):  # Use top 3 sources for context
            # Extract just the main segment text for display, but LLM gets full context
            source_contexts.append(
                f"Source {i} (timestamp {source.timestamp:.1f}s):\n{source.text}"
            )
        
        context_text = "\n\n".join(source_contexts)
        
        # Create prompt for LLM to fix transcription errors
        correction_prompt = f"""Du er en ekspert på å rette transkripsjonsfeil i norsk språk. 
Din oppgave er å rette eventuelle feil i svaret basert på konteksten fra kildesegmentene.

Opprinnelig spørsmål: {query}

Kontekst fra videosegmenter (inkludert omkringliggende setninger):
{context_text}

Svar som skal rettes:
{answer}

Instruksjoner:
1. Identifiser ord som ser ut som transkripsjonsfeil (feilstavet, manglende bokstaver, forvirrende ord)
2. Bruk konteksten fra kildesegmentene til å finne riktige ord - se spesielt på "MAIN SEGMENT" delen
3. Rett kun ord som tydelig er feil - ikke endre korrekt norsk
4. Behold all formatering (som **bold** tekst)
5. Behold all informasjon og betydning
6. Svaret skal fortsatt være naturlig norsk språk

Vanlige feil å se etter:
- "kiveradiver" → "arkivrådgiver"
- "Sandrøy" → "Sandefjord" (hvis konteksten indikerer det)
- Andre ord som ikke gir mening i norsk kontekst

Returner kun det korrigerte svaret, uten forklaringer eller markeringer av endringer."""

        # Use LLM to correct the answer
        corrected_answer = await gpt_4o_mini_complete(correction_prompt)
        
        # Clean up the response (remove any markdown code blocks if LLM added them)
        corrected_answer = corrected_answer.strip()
        if corrected_answer.startswith("```"):
            # Remove markdown code blocks
            lines = corrected_answer.split("\n")
            corrected_answer = "\n".join([line for line in lines if not line.strip().startswith("```")])
        
        logger.info(f"Answer correction applied. Original length: {len(answer)}, Corrected length: {len(corrected_answer)}")
        logger.debug(f"Original: {answer[:200]}...")
        logger.debug(f"Corrected: {corrected_answer[:200]}...")
        
        return corrected_answer
        
    except Exception as e:
        logger.error(f"Error post-processing answer: {e}", exc_info=True)
        # On error, return original answer
        return answer


async def _add_context_to_sources(
    sources: List[MessageSource],
    current_user: User,
    db: Session,
    context_segments: int = 2
) -> List[MessageSource]:
    """Add surrounding segment context to sources for better understanding.
    
    For each source, retrieves the previous and next N segments to provide
    context that can help with transcription error correction.
    """
    from app.models.video import VideoSegment
    
    enhanced_sources = []
    
    for source in sources:
        try:
            # Find the segment
            segment = db.query(VideoSegment).filter(
                VideoSegment.video_id == source.video_id,
                VideoSegment.start_time >= source.timestamp - 0.5,
                VideoSegment.start_time <= source.timestamp + 0.5
            ).first()
            
            if not segment:
                # If exact match not found, get closest segment
                segment = db.query(VideoSegment).filter(
                    VideoSegment.video_id == source.video_id
                ).order_by(
                    (VideoSegment.start_time - source.timestamp).abs()
                ).first()
            
            if segment:
                # Get previous segments
                previous_segments = db.query(VideoSegment).filter(
                    VideoSegment.video_id == source.video_id,
                    VideoSegment.start_time < segment.start_time
                ).order_by(VideoSegment.start_time.desc()).limit(context_segments).all()
                
                # Get next segments
                next_segments = db.query(VideoSegment).filter(
                    VideoSegment.video_id == source.video_id,
                    VideoSegment.start_time > segment.start_time
                ).order_by(VideoSegment.start_time.asc()).limit(context_segments).all()
                
                # Build context text
                context_parts = []
                if previous_segments:
                    context_parts.append("...")
                    for prev_seg in reversed(previous_segments):
                        context_parts.append(prev_seg.text)
                
                context_parts.append(f"[MAIN SEGMENT: {segment.text}]")
                
                if next_segments:
                    for next_seg in next_segments:
                        context_parts.append(next_seg.text)
                    context_parts.append("...")
                
                # Create enhanced source with context
                # Keep original text for display, but add context info
                enhanced_source = MessageSource(
                    video_id=source.video_id,
                    video_title=source.video_title,
                    timestamp=source.timestamp,
                    text=" ".join(context_parts),  # Include context in text for post-processing
                    url=source.url
                )
                enhanced_sources.append(enhanced_source)
            else:
                # If segment not found, use original source
                enhanced_sources.append(source)
                
        except Exception as e:
            logger.error(f"Error adding context to source: {e}", exc_info=True)
            # On error, use original source
            enhanced_sources.append(source)
    
    return enhanced_sources


async def _post_process_answer_with_context(
    answer: str,
    sources: List[MessageSource],
    query: str
) -> str:
    """Post-process the answer to fix transcription errors using context from sources.
    
    Uses LLM to:
    1. Identify potential transcription errors in the answer
    2. Use context from source segments to correct them
    3. Ensure all words make sense in the context
    """
    try:
        # Build context from sources (use the enhanced context text we added)
        source_contexts = []
        for i, source in enumerate(sources[:3], 1):  # Use top 3 sources for context
            # Extract just the main segment text for display, but LLM gets full context
            source_contexts.append(
                f"Source {i} (timestamp {source.timestamp:.1f}s):\n{source.text}"
            )
        
        context_text = "\n\n".join(source_contexts)
        
        # Create prompt for LLM to fix transcription errors
        correction_prompt = f"""Du er en ekspert på å rette transkripsjonsfeil i norsk språk. 
Din oppgave er å rette eventuelle feil i svaret basert på konteksten fra kildesegmentene.

Opprinnelig spørsmål: {query}

Kontekst fra videosegmenter (inkludert omkringliggende setninger):
{context_text}

Svar som skal rettes:
{answer}

Instruksjoner:
1. Identifiser ord som ser ut som transkripsjonsfeil (feilstavet, manglende bokstaver, forvirrende ord)
2. Bruk konteksten fra kildesegmentene til å finne riktige ord - se spesielt på "MAIN SEGMENT" delen
3. Rett kun ord som tydelig er feil - ikke endre korrekt norsk
4. Behold all formatering (som **bold** tekst)
5. Behold all informasjon og betydning
6. Svaret skal fortsatt være naturlig norsk språk

Vanlige feil å se etter:
- "kiveradiver" → "arkivrådgiver"
- "Sandrøy" → "Sandefjord" (hvis konteksten indikerer det)
- Andre ord som ikke gir mening i norsk kontekst

Returner kun det korrigerte svaret, uten forklaringer eller markeringer av endringer."""

        # Use LLM to correct the answer
        corrected_answer = await gpt_4o_mini_complete(correction_prompt)
        
        # Clean up the response (remove any markdown code blocks if LLM added them)
        corrected_answer = corrected_answer.strip()
        if corrected_answer.startswith("```"):
            # Remove markdown code blocks
            lines = corrected_answer.split("\n")
            corrected_answer = "\n".join([line for line in lines if not line.strip().startswith("```")])
        
        logger.info(f"Answer correction applied. Original length: {len(answer)}, Corrected length: {len(corrected_answer)}")
        logger.debug(f"Original: {answer[:200]}...")
        logger.debug(f"Corrected: {corrected_answer[:200]}...")
        
        return corrected_answer
        
    except Exception as e:
        logger.error(f"Error post-processing answer: {e}", exc_info=True)
        # On error, return original answer
        return answer

