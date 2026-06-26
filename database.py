import os
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./fitai.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    name = Column(String, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class UserSyncData(Base):
    __tablename__ = "user_sync_data"

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    payload = Column(Text, nullable=False, default="{}")
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
