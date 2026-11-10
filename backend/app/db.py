import os
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from pgvector.sqlalchemy import Vector

load_dotenv(Path(__file__).parents[1] / '.env')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./mavassist.db')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql+psycopg://', 1)
elif DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg://', 1)
# FastAPI runs sync endpoints on a 40-thread pool, so the connection pool must cover that many
# concurrent requests; the SQLAlchemy default (5 + 10 overflow) caused HTTP 500s at 50 virtual users.
POOL = {} if ':memory:' in DATABASE_URL else dict(pool_size=int(os.getenv('DB_POOL_SIZE', '20')), max_overflow=int(os.getenv('DB_MAX_OVERFLOW', '20')), pool_timeout=10)
engine = create_engine(DATABASE_URL, pool_pre_ping=True, **POOL, **({'connect_args': {'check_same_thread': False}} if DATABASE_URL.startswith('sqlite') else {}))
if DATABASE_URL.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def sqlite_constraints(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
SessionLocal = sessionmaker(engine, expire_on_commit=False)
def now(): return datetime.now(timezone.utc)
class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20), default='student')

class Category(Base):
    __tablename__ = 'categories'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)

class Service(Base):
    __tablename__ = 'services'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    category_id: Mapped[int] = mapped_column(ForeignKey('categories.id'))
    location: Mapped[str] = mapped_column(String(250))
    hours: Mapped[str] = mapped_column(String(250))
    contact: Mapped[str] = mapped_column(String(250))
    source_url: Mapped[str] = mapped_column(String(500))
    tags: Mapped[list] = mapped_column(JSON, default=list)
    next_steps: Mapped[list] = mapped_column(JSON, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    embedding: Mapped[list | None] = mapped_column(Vector(384).with_variant(JSON, 'sqlite'), nullable=True)

class Notice(Base):
    __tablename__ = 'notices'
    id: Mapped[int] = mapped_column(primary_key=True)
    service_id: Mapped[int] = mapped_column(ForeignKey('services.id'))
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class KnowledgeChunk(Base):
    __tablename__ = 'knowledge_chunks'
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(180), unique=True)
    service_id: Mapped[int] = mapped_column(ForeignKey('services.id'), index=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    steps: Mapped[list] = mapped_column(JSON, default=list)
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    source_url: Mapped[str] = mapped_column(String(500))
    reviewed_at: Mapped[str | None] = mapped_column(String(10), nullable=True)
    embedding: Mapped[list | None] = mapped_column(Vector(384).with_variant(JSON, 'sqlite'), nullable=True)

class Bookmark(Base):
    __tablename__ = 'bookmarks'
    __table_args__ = (UniqueConstraint('user_id', 'service_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    service_id: Mapped[int] = mapped_column(ForeignKey('services.id'))

class Recent(Base):
    __tablename__ = 'recent_views'
    __table_args__ = (UniqueConstraint('user_id', 'service_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    service_id: Mapped[int] = mapped_column(ForeignKey('services.id'))
    viewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class UsageEvent(Base):
    __tablename__ = 'usage_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), index=True)
    term: Mapped[str | None] = mapped_column(String(200), nullable=True)
    service_id: Mapped[int | None] = mapped_column(ForeignKey('services.id'), nullable=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey('categories.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)

class ChatLog(Base):
    __tablename__ = 'chat_logs'
    # No user foreign key, question text, IP, session ID, or other account link.
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    service_id: Mapped[int | None] = mapped_column(ForeignKey('services.id'), nullable=True)
    mode: Mapped[str] = mapped_column(String(30))
    helpful: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
