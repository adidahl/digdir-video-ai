"""Neo4j service for knowledge graph storage."""
from typing import List, Dict
from neo4j import Session as Neo4jSession
from app.models.video import Video, VideoSegment
from app.models.user import User, Organization
from app.database import neo4j_conn


class Neo4jService:
    """Service for managing Neo4j graph operations."""
    
    def __init__(self):
        self.conn = neo4j_conn
    
    def create_video_graph(self, video: Video, segments: List[VideoSegment]):
        """Create video and segments in Neo4j graph."""
        with self.conn.get_session() as session:
            # Create organization node
            session.run(
                """
                MERGE (o:Organization {id: $org_id})
                SET o.name = $org_name
                """,
                org_id=str(video.organization_id),
                org_name="Organization"  # Would need to join with org table
            )
            
            # Create video node
            session.run(
                """
                MATCH (o:Organization {id: $org_id})
                MERGE (v:Video {id: $video_id})
                SET v.title = $title,
                    v.status = $status,
                    v.security_level = $security_level
                MERGE (o)-[:OWNS]->(v)
                """,
                org_id=str(video.organization_id),
                video_id=str(video.id),
                title=video.title,
                status=video.status.value,
                security_level=video.security_level.value
            )
            
            # Create segment nodes
            for segment in segments:
                session.run(
                    """
                    MATCH (v:Video {id: $video_id})
                    MERGE (s:VideoSegment {
                        id: $segment_id,
                        video_id: $video_id,
                        segment_idx: $segment_idx
                    })
                    SET s.start_time = $start_time,
                        s.end_time = $end_time,
                        s.text = $text
                    MERGE (v)-[:HAS_SEGMENT]->(s)
                    """,
                    video_id=str(video.id),
                    segment_id=str(segment.id),
                    segment_idx=segment.segment_id,
                    start_time=segment.start_time,
                    end_time=segment.end_time,
                    text=segment.text
                )
    
    def search_related_segments(
        self,
        video_id: str,
        limit: int = 10
    ) -> List[Dict]:
        """Search for related segments in the graph."""
        with self.conn.get_session() as session:
            result = session.run(
                """
                MATCH (v:Video {id: $video_id})-[:HAS_SEGMENT]->(s:VideoSegment)
                RETURN s.id as id, s.text as text, s.start_time as start, s.end_time as end
                ORDER BY s.segment_idx
                LIMIT $limit
                """,
                video_id=video_id,
                limit=limit
            )
            
            return [dict(record) for record in result]

