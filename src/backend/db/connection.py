"""
MedBrief AI — Database Connection & Session Management
Step 3: Database Foundation

Supports PostgreSQL / Supabase connection strings with safe local SQLite fallback
for offline testing and development environments.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

# Load environment configuration
load_dotenv()

# Determine database URL
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if not DATABASE_URL:
    # Safe local development / test database
    DATABASE_URL = "sqlite:///./medbrief_dev.db"
elif DATABASE_URL.startswith("postgres://"):
    # SQLAlchemy 2.0 requires postgresql:// instead of deprecated postgres://
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Configure connection arguments based on database dialect
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False,
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative ORM models
Base = declarative_base()


def get_db():
    """
    FastAPI dependency that yields a transactional database session
    and ensures clean closure after the request terminates.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
