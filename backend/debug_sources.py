"""
Debug script to investigate source extraction issues.
This helps verify why video references don't match the actual answer.
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.lightrag_service import get_lightrag_service
from app.database import SessionLocal
from app.models.video import Video, VideoSegment
from sqlalchemy.orm import Session
import re
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def debug_source_extraction(
    organization_id: str,
    query: str,
    db: Session
):
    """Debug source extraction for a specific query."""
    print(f"\n{'='*80}")
    print(f"DEBUGGING SOURCE EXTRACTION")
    print(f"{'='*80}")
    print(f"Query: {query}")
    print(f"Organization ID: {organization_id}\n")
    
    # Get LightRAG service
    lightrag_service = await get_lightrag_service()
    
    # Step 1: Get raw context from LightRAG
    print("\n[STEP 1] Fetching LightRAG context...")
    lightrag_context = await lightrag_service.search_async(
        organization_id=organization_id,
        query=query,
        mode="mix",
        top_k=10,
        only_need_context=True,
        conversation_history=None,
        user_prompt=None
    )
    
    print(f"\nContext length: {len(lightrag_context)} characters")
    print(f"\n{'='*80}")
    print("RAW LIGHTRAG CONTEXT:")
    print(f"{'='*80}")
    print(lightrag_context)
    print(f"{'='*80}\n")
    
    # Step 2: Extract metadata headers
    print("\n[STEP 2] Extracting metadata headers from context...")
    pattern = r'\[video_id=([^;]+);start=([^;]+);end=([^;]+);segment_id=([^\]]+)\]'
    matches = re.findall(pattern, lightrag_context)
    
    print(f"Found {len(matches)} metadata headers:")
    for i, match in enumerate(matches, 1):
        video_id_str, start_str, end_str, segment_id_str = match
        print(f"  {i}. video_id={video_id_str}, start={start_str}s, end={end_str}s, segment_id={segment_id_str}")
    
    # Step 3: Verify each segment in database
    print(f"\n[STEP 3] Verifying segments in database...")
    for i, match in enumerate(matches, 1):
        video_id_str, start_str, end_str, segment_id_str = match
        start_time = float(start_str)
        
        print(f"\n  Header {i}:")
        print(f"    video_id: {video_id_str}")
        print(f"    start_time: {start_time}s")
        print(f"    segment_id: {segment_id_str}")
        
        # Check if video exists
        video = db.query(Video).filter(Video.id == video_id_str).first()
        if not video:
            print(f"    ❌ ERROR: Video {video_id_str} not found in database!")
            continue
        
        print(f"    ✓ Video found: {video.title}")
        
        # Try to find exact segment
        segment = db.query(VideoSegment).filter(
            VideoSegment.video_id == video_id_str,
            VideoSegment.start_time >= start_time - 0.1,
            VideoSegment.start_time <= start_time + 0.1
        ).first()
        
        if segment:
            print(f"    ✓ Exact segment found at {segment.start_time}s")
            print(f"    Text: {segment.text[:150]}...")
        else:
            print(f"    ⚠️  No exact segment found, searching for approximate match...")
            # Get any segment from this video
            any_segment = db.query(VideoSegment).filter(
                VideoSegment.video_id == video_id_str
            ).first()
            if any_segment:
                print(f"    ⚠️  Using first available segment at {any_segment.start_time}s")
                print(f"    Text: {any_segment.text[:150]}...")
            else:
                print(f"    ❌ ERROR: No segments found for this video!")
    
    # Step 4: Search database for actual segments containing query terms
    print(f"\n[STEP 4] Searching database for segments containing query terms...")
    query_terms = query.lower().split()
    print(f"Query terms: {query_terms}")
    
    all_segments = db.query(VideoSegment).join(Video).filter(
        Video.organization_id == organization_id
    ).all()
    
    matching_segments = []
    for segment in all_segments:
        segment_text_lower = segment.text.lower()
        if any(term in segment_text_lower for term in query_terms if len(term) > 2):
            matching_segments.append(segment)
    
    print(f"\nFound {len(matching_segments)} segments containing query terms:")
    for i, segment in enumerate(matching_segments[:10], 1):  # Show first 10
        print(f"  {i}. Video: {segment.video.title}")
        print(f"     Time: {segment.start_time}s - {segment.end_time}s")
        print(f"     Text: {segment.text[:150]}...")
        print()
    
    # Step 5: Compare LightRAG headers with actual matches
    print(f"\n[STEP 5] Comparing LightRAG headers with actual database matches...")
    header_video_ids = {match[0] for match in matches}
    header_times = {float(match[1]) for match in matches}
    
    matching_video_ids = {str(seg.video_id) for seg in matching_segments}
    matching_times = {seg.start_time for seg in matching_segments}
    
    print(f"\nLightRAG header video IDs: {header_video_ids}")
    print(f"Database matching video IDs: {matching_video_ids}")
    print(f"\nLightRAG header timestamps: {sorted(header_times)}")
    print(f"Database matching timestamps: {sorted(list(matching_times))[:10]}...")  # First 10
    
    if header_video_ids != matching_video_ids:
        print(f"\n⚠️  WARNING: Video IDs don't match!")
    
    # Check if any header times are close to matching times
    time_matches = []
    for header_time in header_times:
        closest_match = min(matching_times, key=lambda t: abs(t - header_time))
        if abs(closest_match - header_time) < 5.0:  # Within 5 seconds
            time_matches.append((header_time, closest_match))
    
    if not time_matches:
        print(f"\n⚠️  WARNING: None of the LightRAG header timestamps match database segments!")
        print(f"    This suggests metadata headers are from different segments than the answer.")
    else:
        print(f"\n✓ Found {len(time_matches)} timestamp matches:")
        for header_time, db_time in time_matches:
            print(f"    Header: {header_time}s ≈ Database: {db_time}s")


async def main():
    """Main function to run debug."""
    # Configuration - adjust these for your test
    organization_id = "test-org"  # Change to your actual org ID
    query = "Var der en person som heter Marting og hvor jobber han?"
    
    db = SessionLocal()
    try:
        await debug_source_extraction(organization_id, query, db)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
