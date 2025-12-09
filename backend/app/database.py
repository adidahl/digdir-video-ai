"""Database connection and session management."""
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from neo4j import GraphDatabase
from redis import Redis
from typing import Generator
from app.config import get_settings

settings = get_settings()

# PostgreSQL
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Enable pgvector extension on connect
@event.listens_for(engine, "connect")
def enable_pgvector(dbapi_conn, connection_record):
    """Enable pgvector extension on connection."""
    cursor = dbapi_conn.cursor()
    try:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
        dbapi_conn.commit()
    except Exception:
        dbapi_conn.rollback()
    finally:
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Get database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Neo4j
class Neo4jConnection:
    """Neo4j database connection manager."""
    
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
    
    def close(self):
        """Close the Neo4j driver connection."""
        if self.driver:
            self.driver.close()
    
    def get_session(self):
        """Get a Neo4j session."""
        return self.driver.session()


neo4j_conn = Neo4jConnection()


def get_neo4j():
    """Get Neo4j session dependency."""
    session = neo4j_conn.get_session()
    try:
        yield session
    finally:
        session.close()


# Redis
redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


def get_redis() -> Redis:
    """Get Redis client dependency."""
    return redis_client

