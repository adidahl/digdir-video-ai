# Video RAG Platform

A production-ready multi-tenant video search platform with RAG capabilities, featuring JWT authentication, role-based access control, async video processing with Whisper, vector/graph storage, and a modern React frontend with Designsystemet UI library supporting 3 languages (English, Norwegian Bokmål, Norwegian Nynorsk).

## Features

- **Multi-tenant Architecture**: Organizations with role-based access control (Super Admin, Org Admin, User)
- **Video Processing**: Automatic transcription using OpenAI Whisper (large model)
- **Semantic Search**: Vector search with pgvector and LightRAG for semantic understanding
- **Knowledge Graph**: Neo4j graph database for relationships and entity extraction
- **Modern UI**: React frontend with Norwegian Designsystemet components
- **Internationalization**: Support for English, Norwegian Bokmål, and Norwegian Nynorsk
- **Security Levels**: Public, Internal, Confidential, Secret video classification
- **Async Processing**: Celery workers for video transcription tasks

## Technology Stack

### Backend
- **FastAPI** - REST API framework
- **Python 3.11+**
- **Celery + Redis** - Async task processing
- **OpenAI Whisper** - Video transcription
- **LightRAG** - Semantic search and RAG
- **Alembic** - Database migrations
- **JWT** - Authentication
- **SQLAlchemy** - ORM

### Frontend
- **Vite + React + TypeScript**
- **Designsystemet** (@digdir/designsystemet-react)
- **React Router v6**
- **React Query** - Data fetching
- **i18next** - Internationalization
- **Axios** - HTTP client

### Databases
- **PostgreSQL** - Users, videos, metadata, organizations
- **PostgreSQL with pgvector** - Vector embeddings
- **Neo4j** - Knowledge graph
- **Redis** - Celery broker + result backend

## Quick Start

### Prerequisites

- Docker and Docker Compose
- OpenAI API key (for Whisper and embeddings)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd digdir-video-ai
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` and add your OpenAI API key:

```bash
OPENAI_API_KEY=sk-your-api-key-here
JWT_SECRET_KEY=your-random-secret-key-here
```

### 3. Start Services

```bash
docker-compose up -d
```

This will start:
- PostgreSQL (port 5432)
- Neo4j (ports 7474, 7687)
- Redis (port 6379)
- Backend API (port 8000)
- Celery Worker
- Frontend (port 5173)

### 4. Access the Application

- **Frontend**: http://localhost:5173
- **API Documentation**: http://localhost:8000/api/docs
- **Neo4j Browser**: http://localhost:7474

### 5. Create First User

1. Navigate to http://localhost:5173
2. Click "Register"
3. Fill in:
   - Email
   - Password (min 8 characters)
   - Full Name
   - Organization Name

The first user of an organization is automatically assigned the `org_admin` role.

## Development

### Backend Development

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

### Run Tests

Backend:
```bash
cd backend
pytest
```

Frontend:
```bash
cd frontend
npm run test
```

## Database Migrations

Create a new migration:

```bash
cd backend
alembic revision --autogenerate -m "Description of changes"
```

Apply migrations:

```bash
alembic upgrade head
```

Rollback:

```bash
alembic downgrade -1
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/auth/me` - Get current user info

### Videos
- `POST /api/videos/upload` - Upload video (multipart/form-data)
- `GET /api/videos/` - List accessible videos
- `GET /api/videos/{id}` - Get video details
- `GET /api/videos/{id}/segments` - Get video segments with transcriptions
- `PATCH /api/videos/{id}` - Update video metadata
- `DELETE /api/videos/{id}` - Delete video

### Search
- `POST /api/search/` - Semantic search across videos
- `GET /api/search/lightrag/{query}` - Advanced RAG search

### Admin
- `GET /api/admin/organizations` - List organizations (super admin)
- `POST /api/admin/organizations` - Create organization (super admin)
- `GET /api/admin/organizations/{id}/users` - List org users
- `GET /api/admin/organizations/{id}/stats` - Get org statistics

### Users
- `GET /api/users/` - List users in organization
- `POST /api/users/` - Create user (org admin+)
- `GET /api/users/{id}` - Get user details
- `PATCH /api/users/{id}` - Update user
- `DELETE /api/users/{id}` - Delete user (super admin)

## Architecture

### Video Processing Flow

1. User uploads video via `/api/videos/upload`
2. Video saved to Docker volume, database record created with status="processing"
3. Celery task triggered: `transcribe_video.delay(video_id)`
4. Whisper transcribes video → segments with timestamps
5. Segments saved to PostgreSQL + embeddings to pgvector
6. LightRAG processes transcripts (organization-specific working directory)
7. Neo4j graph updated with entities and relationships
8. Video status updated to "completed"
9. Frontend can now search and view transcriptions

### Access Control

- **Super Admin**: Access to all organizations and videos
- **Org Admin**: Access to all videos in their organization, can manage users
- **User**: Access to videos based on organization membership and security level

### Security Levels

- **Public**: All organization members can access
- **Internal**: All organization members can access
- **Confidential**: Org admins and explicitly granted users
- **Secret**: Org admins and explicitly granted users

## Multi-Tenancy

Each organization has:
- Separate LightRAG working directory: `/app/lightrag_store/org_{organization_id}/`
- Isolated video storage: `/app/videos/{organization_id}/`
- Filtered database queries based on `organization_id`

## Configuration

Key environment variables:

- `DATABASE_URL`: PostgreSQL connection string
- `NEO4J_URI`: Neo4j connection URI
- `NEO4J_USER`, `NEO4J_PASSWORD`: Neo4j credentials
- `REDIS_URL`: Redis connection string
- `JWT_SECRET_KEY`: Secret key for JWT signing
- `OPENAI_API_KEY`: OpenAI API key for Whisper and embeddings
- `WHISPER_MODEL`: Whisper model size (tiny, base, small, medium, large, turbo)
- `VIDEO_STORAGE_PATH`: Path for video file storage
- `LIGHTRAG_STORAGE_PATH`: Path for LightRAG working directories

## Production Deployment

### Security Checklist

- [ ] Change `JWT_SECRET_KEY` to a strong random value
- [ ] Use strong database passwords
- [ ] Enable HTTPS with TLS certificates
- [ ] Configure rate limiting on API endpoints
- [ ] Set up firewall rules
- [ ] Enable database backups
- [ ] Configure log aggregation
- [ ] Set up monitoring (Prometheus/Grafana)

### Performance Optimization

- Horizontal scaling of Celery workers for faster video processing
- Database connection pooling (already configured)
- CDN for frontend assets
- Video streaming optimization with chunked transfer
- Redis caching for frequently accessed data

### Backup Strategy

- Database: Daily PostgreSQL backups
- Neo4j: Regular graph database backups
- Videos: Backup to S3-compatible storage
- LightRAG data: Include in backup strategy

## Troubleshooting

### Video transcription fails

Check Celery worker logs:
```bash
docker-compose logs celery-worker
```

Common issues:
- ffmpeg not installed in Docker image
- Insufficient memory for Whisper model
- OpenAI API key not configured

### Database connection errors

Check if PostgreSQL is running:
```bash
docker-compose ps postgres
```

Check connection settings in `.env` file.

### Frontend can't connect to backend

- Verify `VITE_API_BASE_URL` in frontend `.env`
- Check CORS settings in `backend/app/main.py`
- Ensure backend is running on port 8000

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## Support

For issues and questions, please open an issue on GitHub.
