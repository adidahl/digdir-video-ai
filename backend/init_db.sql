-- Initialize database with required extensions

-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Optional: Create other useful extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text similarity search

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE videorag TO videorag;

