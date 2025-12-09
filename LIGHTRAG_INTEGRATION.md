# LightRAG Integration Summary

## Overview

The Video RAG Platform now uses **LightRAG** as its core search and knowledge extraction engine. LightRAG replaces the previous simple pgvector search with a sophisticated system that combines:

1. **Entity Extraction**: Automatically identifies entities and relationships from video transcripts
2. **Knowledge Graph**: Builds a comprehensive graph of entities and their relationships in Neo4j
3. **Vector Search**: Uses pgvector for semantic similarity search on chunks
4. **Mix Mode**: Combines knowledge graph + vector retrieval for optimal results

## Architecture Changes

### What Changed

1. **Configuration** (`backend/app/config.py`)
   - Added `lightrag_use_external_storage` flag
   - Added `lightrag_embedding_model` and `lightrag_llm_model` settings
   - Configured to use external PostgreSQL and Neo4j storage backends

2. **LightRAG Service** (`backend/app/services/lightrag_service.py`)
   - Complete rewrite with proper async initialization
   - Configured PostgreSQL storage backends (PGKVStorage, PGVectorStorage, PGGraphStorage, PGDocStatusStorage)
   - Configured Neo4j for graph data
   - Workspace-based isolation per organization (format: `org_{organization_id}`)
   - Proper lifecycle management (init/finalize storages)

3. **Video Processor** (`backend/app/services/video_processor.py`)
   - Removed manual embedding generation (LightRAG handles this)
   - Integrated with LightRAG for automatic entity extraction
   - Keeps VideoSegment records in PostgreSQL for reference
   - Added metadata headers to each segment: `[video_id=X;start=Y;end=Z;segment_id=N]`

4. **Search API** (`backend/app/api/search.py`)
   - Replaced pgvector cosine similarity with LightRAG "mix" mode
   - Parses LightRAG context to extract video segments with timestamps
   - Added `/lightrag/{query}` endpoint for LLM-generated answers
   - Supports multiple query modes: mix, hybrid, local, global, naive

5. **Celery Tasks** (`backend/app/tasks/video_tasks.py`)
   - Updated to use async-aware video processor
   - Properly handles LightRAG processing in background

6. **FastAPI Lifecycle** (`backend/app/main.py`)
   - Added startup event to initialize LightRAG service
   - Added shutdown event to properly close all LightRAG instances

## How It Works

### Video Processing Pipeline

1. **Upload**: User uploads video via `/api/videos/uploadfile`
2. **Transcription**: Celery task uses OpenAI Whisper to transcribe
3. **Segmentation**: Creates VideoSegment records in PostgreSQL
4. **LightRAG Processing**:
   - Formats segments with metadata headers
   - Sends to LightRAG for processing
   - LightRAG extracts entities and relationships using GPT-4o-mini
   - Stores embeddings in pgvector
   - Stores knowledge graph in Neo4j
   - All data is isolated per organization using workspace parameter

### Search Flow

1. **User Query**: User searches via `/api/search/`
2. **LightRAG Query**: 
   - Uses "mix" mode (knowledge graph + vector)
   - Returns context with metadata headers
3. **Parse Results**:
   - Extracts video IDs and timestamps from headers
   - Fetches VideoSegment records from PostgreSQL
   - Applies access control based on user permissions
4. **Return Results**: Structured response with video info and timestamps

## Storage Backends

### PostgreSQL (via pgvector)
- **Purpose**: Stores vectors, key-value pairs, document status
- **Tables**: LightRAG auto-creates tables for its storage backends
- **Isolation**: Per-organization via workspace parameter

### Neo4j
- **Purpose**: Stores entity/relationship knowledge graph
- **Structure**: Entities as nodes, relationships as edges
- **Isolation**: Per-organization via workspace parameter

## Query Modes

LightRAG supports multiple query modes via `/lightrag/{query}`:

1. **mix** (recommended): Knowledge graph + vector retrieval
2. **hybrid**: Combines local entities + global communities
3. **local**: Entity-focused retrieval
4. **global**: High-level community summaries  
5. **naive**: Simple vector search on chunks

## Testing the Integration

### 1. Check Services
```bash
docker-compose ps
# All services should be "Up" and "healthy"
```

### 2. Upload a Test Video
```bash
# Via frontend: http://localhost:5173/admin
# Or via API:
curl -X POST "http://localhost:8000/api/videos/uploadfile" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@video.mp4" \
  -F "title=Test Video" \
  -F "security_level=public"
```

### 3. Monitor Processing
```bash
# Check Celery logs
docker-compose logs -f celery-worker

# Look for:
# - "Processing X segments with LightRAG"
# - "Inserted video X into LightRAG for org Y"
# - "LightRAG processing completed for video X"
```

### 4. Verify Database Storage

**PostgreSQL (VideoSegments):**
```bash
docker-compose exec postgres psql -U postgres -d videorag -c "SELECT COUNT(*) FROM video_segments;"
```

**Neo4j (Knowledge Graph):**
```bash
# Open Neo4j Browser: http://localhost:7474
# Username: neo4j, Password: neo4jpassword
# Run Cypher query:
MATCH (n) RETURN n LIMIT 25
```

### 5. Test Search

**Via Frontend:**
- Navigate to http://localhost:5173/search
- Enter a query related to your video content
- Results should include relevant timestamps

**Via API:**
```bash
# Structured search (returns video segments)
curl -X POST "http://localhost:8000/api/search/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "your search term", "top_k": 5}'

# LightRAG answer (returns LLM-generated response)
curl "http://localhost:8000/api/search/lightrag/your%20search%20term" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Troubleshooting

### Issue: "Shared dictionaries not initialized"
**Solution**: This occurs if `initialize_pipeline_status()` is called before any RAG instance is created. Fixed in current implementation.

### Issue: OpenAI RateLimitError
**Solution**: Ensure `OPENAI_API_KEY` and `OPENAI_ORG_ID` are set in `.env` file and you have sufficient credits.

### Issue: No search results
**Possible causes**:
1. Video not yet processed (check status in database)
2. LightRAG processing failed (check Celery logs)
3. Query doesn't match content (try broader terms)

### Issue: Celery worker not processing
**Solution**: 
```bash
docker-compose restart celery-worker
docker-compose logs celery-worker
```

## Performance Considerations

### LightRAG Processing Time
- Entity extraction uses LLM (GPT-4o-mini), which takes time
- Long videos may take several minutes to process
- Processing is asynchronous via Celery

### Search Performance
- Knowledge graph queries can be slower than pure vector search
- "mix" mode provides best accuracy but takes ~2-3 seconds
- Consider using "naive" mode for faster, simpler searches

### Scaling
- Each organization gets its own workspace for data isolation
- PostgreSQL and Neo4j can handle thousands of organizations
- Consider connection pooling for high-traffic scenarios

## Environment Variables

Required in `.env`:

```bash
# OpenAI (required for LightRAG)
OPENAI_API_KEY=sk-...
OPENAI_ORG_ID=org-...  # Required if using organization account

# Database URLs (auto-configured)
DATABASE_URL=postgresql://postgres:password@postgres:5432/videorag
NEO4J_URI=bolt://neo4j:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=neo4jpassword

# LightRAG Configuration (optional overrides)
LIGHTRAG_USE_EXTERNAL_STORAGE=true
LIGHTRAG_EMBEDDING_MODEL=text-embedding-ada-002
LIGHTRAG_LLM_MODEL=gpt-4o-mini
```

## Next Steps

1. **Monitor First Video Processing**: Upload a test video and monitor the entire pipeline
2. **Test Search Quality**: Try various queries to evaluate LightRAG's effectiveness
3. **Check Neo4j Graph**: Visualize the extracted knowledge graph in Neo4j Browser
4. **Production Optimization**: Consider caching, connection pooling, and error recovery strategies
5. **User Testing**: Have real users test the search functionality with their queries

## Resources

- [LightRAG GitHub](https://github.com/hkuds/lightrag)
- [LightRAG Documentation](https://lightrag.readthedocs.io/)
- [Neo4j Browser Guide](https://neo4j.com/docs/browser-manual/current/)
- [pgvector Documentation](https://github.com/pgvector/pgvector)

