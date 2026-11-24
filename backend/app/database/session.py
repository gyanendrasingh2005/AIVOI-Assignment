import time
import socket
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import text
from app.core.config import settings
from app.core.logging import logger


def is_database_reachable(host: str, port: int, timeout: float = 0.5) -> bool:
    """Synchronously checks if the database host and port are listening."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


# Initialize async engine with connection pooling
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    pool_pre_ping=True,
    connect_args={"timeout": 2.0},
)

# Configure session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection helper providing a scoped async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session rolled back due to error: {e}")
            raise
        finally:
            await session.close()


async def check_database_connection() -> dict:
    """Verifies PostgreSQL connectivity and returns response latency."""
    start_time = time.time()
    
    # 1. Quick pre-flight socket probe to prevent socket hangs if database is offline
    host = settings.POSTGRES_SERVER
    if host == "localhost":
        host = "127.0.0.1"
    port = settings.POSTGRES_PORT
    
    if not is_database_reachable(host, port, timeout=0.5):
        latency_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "connected": False,
            "database": settings.POSTGRES_DB,
            "latency_ms": latency_ms,
            "error": f"PostgreSQL port {port} on {host} is unreachable or offline.",
        }

    # 2. Live query execution if port is open
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            val = result.scalar()
            latency_ms = round((time.time() - start_time) * 1000, 2)
            if val == 1:
                return {
                    "connected": True,
                    "database": settings.POSTGRES_DB,
                    "latency_ms": latency_ms,
                    "error": None,
                }
            return {
                "connected": False,
                "database": settings.POSTGRES_DB,
                "latency_ms": latency_ms,
                "error": "Unexpected return value",
            }
    except Exception as exc:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        logger.warning(f"Database query check failed: {exc}")
        return {
            "connected": False,
            "database": settings.POSTGRES_DB,
            "latency_ms": latency_ms,
            "error": str(exc),
        }
