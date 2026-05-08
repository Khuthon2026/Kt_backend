import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

load_dotenv()


def _normalize_database_url(raw_url: str) -> str:
    if raw_url.startswith("postgres://"):
        return raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
    if raw_url.startswith("postgresql://") and "+asyncpg" not in raw_url:
        return raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return raw_url


DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DATABASE_URL = _normalize_database_url(DATABASE_URL) if DATABASE_URL else ""

Base = declarative_base()

_engine = create_async_engine(DATABASE_URL, pool_pre_ping=True) if DATABASE_URL else None
async_session_maker: async_sessionmaker[AsyncSession] | None = (
    async_sessionmaker(_engine, expire_on_commit=False) if _engine else None
)


def is_db_configured() -> bool:
    return bool(_engine)


async def init_db() -> None:
    if not _engine:
        return
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
