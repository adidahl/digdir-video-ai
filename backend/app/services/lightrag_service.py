"""LightRAG service for semantic search with knowledge graph extraction."""
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import asyncio
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed
from lightrag.kg.shared_storage import initialize_pipeline_status
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class LightRAGService:
    """Service for managing LightRAG instances per organization with external storage."""
    
    def __init__(self):
        self.base_path = Path(settings.lightrag_storage_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._instances: Dict[str, LightRAG] = {}
        self._initialized = False
        
        # Configure environment variables for PostgreSQL and Neo4j
        self._setup_storage_env()
    
    def _setup_storage_env(self):
        """Setup environment variables for LightRAG external storage."""
        if not settings.lightrag_use_external_storage:
            return
        
        # Parse database URL for PostgreSQL configuration
        # Expected format: postgresql://user:password@host:port/database
        if settings.database_url:
            from urllib.parse import urlparse
            parsed = urlparse(settings.database_url)
            
            os.environ["POSTGRES_HOST"] = parsed.hostname or "localhost"
            os.environ["POSTGRES_PORT"] = str(parsed.port or 5432)
            os.environ["POSTGRES_USER"] = parsed.username or "postgres"
            os.environ["POSTGRES_PASSWORD"] = parsed.password or ""
            # LightRAG expects POSTGRES_DATABASE (not POSTGRES_DB)
            os.environ["POSTGRES_DATABASE"] = parsed.path.lstrip("/") if parsed.path else "videorag"
        
        # Configure Neo4j
        if settings.neo4j_uri:
            os.environ["NEO4J_URI"] = settings.neo4j_uri
            os.environ["NEO4J_USERNAME"] = settings.neo4j_user
            os.environ["NEO4J_PASSWORD"] = settings.neo4j_password
        
        logger.info("LightRAG external storage environment configured")
    
    async def initialize_service(self):
        """Initialize the LightRAG service."""
        if not self._initialized:
            self._initialized = True
            logger.info("LightRAG service initialized")
    
    async def get_rag_instance(self, organization_id: str) -> LightRAG:
        """Get or create LightRAG instance for an organization."""
        if organization_id not in self._instances:
            workspace = f"org_{organization_id}"
            org_dir = self.base_path / workspace
            org_dir.mkdir(parents=True, exist_ok=True)
            
            # Configure storage backends
            storage_config = {}
            if settings.lightrag_use_external_storage:
                storage_config = {
                    "kv_storage": "PGKVStorage",
                    "vector_storage": "PGVectorStorage",
                    "graph_storage": "Neo4JStorage",
                    "doc_status_storage": "PGDocStatusStorage",
                    "workspace": workspace,  # Logical isolation per organization
                }
            
            # Initialize LightRAG instance
            rag = LightRAG(
                working_dir=str(org_dir),
                embedding_func=openai_embed,
                llm_model_func=gpt_4o_mini_complete,
                **storage_config
            )
            
            # Initialize storages
            await rag.initialize_storages()
            
            # Initialize pipeline status on first RAG instance creation
            if len(self._instances) == 0:
                await initialize_pipeline_status()
                logger.info("LightRAG pipeline status initialized")
            
            self._instances[organization_id] = rag
            logger.info(f"Created LightRAG instance for organization {organization_id}")
        
        return self._instances[organization_id]
    
    async def process_video_transcript_async(
        self,
        organization_id: str,
        video_id: str,
        transcript: str,
        segments: List[Dict[str, Any]]
    ):
        """Process video transcript with LightRAG (async version).
        
        LightRAG will automatically:
        - Extract entities and relationships using LLM
        - Generate embeddings for chunks, entities, and relationships
        - Store everything in configured backends (PostgreSQL + Neo4j)
        """
        rag = await self.get_rag_instance(organization_id)
        
        # Build context with metadata headers as in notebook
        contexts = []
        for seg in segments:
            text = seg.get("text", "").strip()
            if text:
                header = (
                    f"[video_id={video_id};start={seg.get('start', 0)};"
                    f"end={seg.get('end', 0)};segment_id={seg.get('id', 0)}] "
                )
                contexts.append(header + text)
        
        # Join contexts and insert into LightRAG with document ID for tracking
        if contexts:
            joined_contexts = "\n\n".join(contexts)
            doc_id = f"video-{video_id}"
            
            try:
                await rag.ainsert(joined_contexts, ids=[doc_id])
                logger.info(f"Inserted video {video_id} into LightRAG for org {organization_id}")
            except Exception as e:
                logger.error(f"Failed to insert video {video_id} into LightRAG: {e}")
                raise
    
    async def search_async(
        self,
        organization_id: str,
        query: str,
        mode: str = "mix",
        top_k: int = 5,
        only_need_context: bool = False,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_prompt: Optional[str] = None
    ) -> str:
        """Search using LightRAG with knowledge graph + vector retrieval.
        
        Args:
            organization_id: Organization ID for workspace isolation
            query: User's search query
            mode: Query mode - "mix" combines knowledge graph + vector retrieval
            top_k: Number of top results
            only_need_context: If True, return only context without LLM generation
            conversation_history: List of previous messages for context
                Format: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
            user_prompt: Custom prompt instructions for the LLM
        
        Returns:
            LightRAG query result (generated answer or raw context)
        """
        rag = await self.get_rag_instance(organization_id)
        
        try:
            # Build QueryParam with conversation history if provided
            query_param = QueryParam(
                mode=mode,
                top_k=top_k,
                only_need_context=only_need_context
            )
            
            # Add conversation history for memory/context
            if conversation_history:
                query_param.conversation_history = conversation_history
            
            # Add custom prompt for conversational responses
            if user_prompt:
                query_param.user_prompt = user_prompt
            
            result = await rag.aquery(
                query,
                param=query_param
            )
            return result
        except Exception as e:
            logger.error(f"LightRAG search failed for org {organization_id}: {e}")
            raise
    
    async def delete_video_async(
        self,
        organization_id: str,
        video_id: str
    ):
        """Delete a video's data from LightRAG.
        
        This performs smart cleanup:
        - Removes entities/relations unique to this video
        - Preserves shared knowledge
        - Rebuilds affected entity descriptions
        """
        rag = await self.get_rag_instance(organization_id)
        doc_id = f"video-{video_id}"
        
        try:
            await rag.adelete_by_doc_id(doc_id)
            logger.info(f"Deleted video {video_id} from LightRAG for org {organization_id}")
        except Exception as e:
            logger.error(f"Failed to delete video {video_id} from LightRAG: {e}")
            raise
    
    async def finalize_all(self):
        """Finalize all LightRAG instances and close connections."""
        for org_id, rag in self._instances.items():
            try:
                await rag.finalize_storages()
                logger.info(f"Finalized LightRAG instance for organization {org_id}")
            except Exception as e:
                logger.error(f"Error finalizing LightRAG for org {org_id}: {e}")
        
        self._instances.clear()
        self._initialized = False
        logger.info("LightRAG service finalized")


# Global service instance
_lightrag_service: Optional[LightRAGService] = None


async def get_lightrag_service() -> LightRAGService:
    """Get or create the global LightRAG service instance."""
    global _lightrag_service
    
    if _lightrag_service is None:
        _lightrag_service = LightRAGService()
        await _lightrag_service.initialize_service()
    
    return _lightrag_service


async def shutdown_lightrag_service():
    """Shutdown the global LightRAG service."""
    global _lightrag_service
    
    if _lightrag_service is not None:
        await _lightrag_service.finalize_all()
        _lightrag_service = None
