# Getting Started with Video RAG Platform

## Quick Start Guide

This guide will help you get the Video RAG Platform up and running in under 10 minutes.

## Prerequisites

Before you begin, ensure you have:

1. **Docker Desktop** installed and running
2. **OpenAI API Key** - Get one at https://platform.openai.com/api-keys
3. **Git** installed

## Step 1: Clone and Setup

```bash
# Clone the repository
cd digdir-video-ai

# Create environment file from example
cp .env.example .env
```

## Step 2: Configure Environment Variables

Open `.env` file and set your OpenAI API key:

```bash
# Required: Your OpenAI API Key
OPENAI_API_KEY=sk-your-actual-api-key-here

# Optional: Change JWT secret for production
JWT_SECRET_KEY=change-this-to-a-random-secret-in-production
```

**Important**: The OpenAI API key is required for:
- Video transcription with Whisper
- Generating embeddings for semantic search
- LightRAG entity extraction and knowledge graph generation

**Note**: If you're using an OpenAI organization account, also add:
```bash
OPENAI_ORG_ID=org-your-organization-id
```

## Step 3: Start the Platform

```bash
# Start all services with Docker Compose
docker-compose up -d

# This will start:
# - PostgreSQL (database)
# - Neo4j (knowledge graph)
# - Redis (task queue)
# - Backend API
# - Celery worker (video processing)
# - Frontend

# View logs (optional)
docker-compose logs -f
```

## Step 4: Access the Application

Once all services are running:

1. **Frontend**: Open http://localhost:5173
2. **API Docs**: Open http://localhost:8000/api/docs
3. **Neo4j Browser**: Open http://localhost:7474 (credentials: neo4j/neo4j123456)

## Step 5: Create Your First Account

1. Navigate to http://localhost:5173
2. Click "Register" or "Registrer" (depending on language)
3. Fill in the registration form:
   - **Email**: your-email@example.com
   - **Password**: At least 8 characters
   - **Full Name**: Your Name
   - **Organization Name**: Your Company Name

4. Click "Create Account"

**Note**: The first user to register for an organization automatically becomes an **Organization Admin**.

## Step 6: Upload Your First Video

1. After logging in, navigate to the **Admin** section
2. Click on the **Upload Video** tab
3. Select a video file from your computer (supports all major video formats)
4. Fill in:
   - **Title**: Name of your video
   - **Description**: Brief description (optional)
   - **Security Level**: Choose access level
     - Public: All org members
     - Internal: All org members (default)
     - Confidential: Admins only
     - Secret: Admins only

5. Click **Upload**

## Step 7: Wait for Processing

After uploading:

1. The video is automatically sent to the Celery worker
2. OpenAI Whisper transcribes the audio (this takes 1-5 minutes depending on video length)
3. Transcripts are saved with timestamps
4. Embeddings are generated for semantic search
5. Knowledge graph is updated in Neo4j

**Check processing status**:
- Go to Admin → Videos tab
- Your video status will change from "processing" to "completed"

## Step 8: Search Your Videos

1. Navigate to the **Search** page
2. Type a natural language query, for example:
   - "What did they say about the project timeline?"
   - "Når snakker de om datadeling?" (if video is in Norwegian)
3. Results show:
   - Video title
   - Relevant segment with timestamp
   - Relevance score
4. Click on any result to jump to that timestamp in the video

## Understanding Roles

### Super Admin
- Access to all organizations
- Can create and delete organizations
- Manage all users across the platform

### Organization Admin
- Manage users within their organization
- Upload and manage videos
- Access all videos in their organization
- View organization statistics

### User
- Search videos in their organization
- View videos based on security level
- Cannot upload or manage content

## Changing Language

Click the language selector in the header:
- **English** (EN)
- **Norsk Bokmål** (NB)
- **Norsk Nynorsk** (NN)

The interface language changes, but video content and transcriptions remain in their original language.

## Common Tasks

### Add a New User to Your Organization

1. Go to **Admin** → **Users**
2. Click **Create User**
3. Fill in user details
4. Assign role (User or Org Admin)
5. The new user can now log in

### View Video Transcript

1. Search for a video or browse from Admin → Videos
2. Click on the video title
3. The transcript appears below the video player
4. Each segment shows timestamp and text

### Advanced Search with LightRAG

For complex queries, use the LightRAG endpoint:

```bash
curl http://localhost:8000/api/search/lightrag/your-query-here \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Troubleshooting

### Videos Stuck in "Processing"

Check Celery worker logs:
```bash
docker-compose logs celery-worker
```

Common causes:
- OpenAI API key not set or invalid
- Insufficient memory (Whisper large model needs ~8GB RAM)
- ffmpeg not available (should be in Docker image)

### Can't Login

1. Verify services are running: `docker-compose ps`
2. Check backend logs: `docker-compose logs backend`
3. Ensure database is healthy: `docker-compose logs postgres`

### Search Returns No Results

1. Verify video processing completed (status = "completed")
2. Check if embeddings were generated
3. Ensure user has access to the videos (organization + security level)

### Frontend Can't Connect to Backend

1. Check backend is running: `curl http://localhost:8000/health`
2. Verify `VITE_API_BASE_URL` in frontend/.env
3. Check browser console for CORS errors

### Database Connection Errors

If you see `database "videorag" does not exist`:

```bash
# Stop all containers
docker-compose down

# Remove the postgres volume to start fresh
docker volume rm digdir-video-ai_postgres_data

# Rebuild and restart
docker-compose up -d --build
```

### SQLAlchemy "metadata" Attribute Error

This has been fixed in the codebase. If you still see this error:
1. Make sure you're using the latest version of the code
2. The `Video` model uses `video_metadata` instead of `metadata` to avoid conflicts

### Dependency Conflicts

If you see pytest version conflicts during build:
1. The requirements.txt has been updated to use compatible versions
2. Rebuild the backend: `docker-compose build backend celery-worker`

## Next Steps

- **Explore API**: Visit http://localhost:8000/api/docs for interactive API documentation
- **Check Database**: Use Neo4j browser to explore the knowledge graph
- **Customize**: Modify security levels, add metadata fields, adjust Whisper model size
- **Scale**: Add more Celery workers for faster video processing

## LightRAG Integration

The platform uses **LightRAG** for advanced knowledge extraction and semantic search. LightRAG automatically:
- Extracts entities and relationships from video transcripts
- Builds a knowledge graph in Neo4j
- Combines graph-based and vector-based retrieval for optimal results

📖 **For detailed information about the LightRAG integration, see [LIGHTRAG_INTEGRATION.md](LIGHTRAG_INTEGRATION.md)**

## Need Help?

- **LightRAG Integration Guide**: [LIGHTRAG_INTEGRATION.md](LIGHTRAG_INTEGRATION.md)
- **API Documentation**: http://localhost:8000/api/docs
- **README**: See README.md for detailed architecture and configuration
- **GitHub Issues**: Report bugs or request features

## Production Checklist

Before deploying to production:

- [ ] Change `JWT_SECRET_KEY` to a strong random value
- [ ] Use secure database passwords
- [ ] Enable HTTPS
- [ ] Set up automatic backups
- [ ] Configure monitoring
- [ ] Review security levels for your use case
- [ ] Test with multiple organizations
- [ ] Set resource limits for Celery workers

---

**Congratulations!** You now have a fully functional video search platform with semantic search capabilities. Start uploading videos and exploring the power of RAG-based video search.

