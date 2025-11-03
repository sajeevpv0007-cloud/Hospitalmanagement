"""
db.py
=====
Handles database connection and session management for the hospital system.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Database path (from environment or default to local SQLite file)
DB_PATH = os.getenv("HMS_DB", "data/hms.db")
DB_DIR = os.path.dirname(DB_PATH)

# Create directory if it doesn’t exist
if DB_DIR and not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR, exist_ok=True)

# SQLAlchemy database URL
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# For SQLite, we must disable thread check
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

# Create a configured session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Dependency injection generator.
    Yields a database session, closes when done.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(Base):
    """
    Initializes the database — creates tables if missing.
    Called once on FastAPI startup.
    """
    Base.metadata.create_all(bind=engine)

