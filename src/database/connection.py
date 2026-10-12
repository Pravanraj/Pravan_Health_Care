"""Database connection setup, engine configuration, and session lifecycle."""

import os
import sys
from typing import Generator
import bcrypt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Fix Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.database.models import Base, User

# Default to SQLite local database, or use PostgreSQL/MySQL if configured
DEFAULT_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "healthcare.db"))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def hash_pw(password: str) -> str:
    """Helper to hash password with bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def get_db() -> Generator[Session, None, None]:
    """Dependency for yielding a transactional database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def seed_default_users(db: Session) -> None:
    """Seed initial default accounts for Role-Based Access Control."""
    defaults = [
        {
            "username": "admin",
            "password": "AdminPassword123!",
            "role": "administrator",
            "full_name": "Chief Medical Officer (Admin)",
        },
        {
            "username": "clinician",
            "password": "ClinicianPass123!",
            "role": "clinical_operations",
            "full_name": "Dr. Sarah Adams (Operations)",
        },
        {
            "username": "analyst",
            "password": "AnalystPass123!",
            "role": "analyst",
            "full_name": "Alex Taylor (Data Analyst)",
        },
    ]

    for user_info in defaults:
        existing = db.query(User).filter(User.username == user_info["username"]).first()
        if not existing:
            hashed = hash_pw(user_info["password"])
            user = User(
                username=user_info["username"],
                hashed_password=hashed,
                role=user_info["role"],
                full_name=user_info["full_name"],
                is_active=True,
            )
            db.add(user)
    db.commit()


def init_db() -> None:
    """Initialize tables in database and seed initial roles."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_default_users(db)
