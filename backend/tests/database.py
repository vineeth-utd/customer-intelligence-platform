"""Dedicated test database infrastructure, safety guard, and isolation management.

Ensures automated tests connect strictly to `cip_test_db` (or a configured
`TEST_DATABASE_URL`), never fall back to or touch `cip_db`, and verify safety
before executing any destructive operation.
"""

import asyncio
import os
from urllib.parse import urlparse

import asyncpg
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config.settings import settings
from app.services.merchant import initialize_reference_data


class DatabaseSafetyViolationError(RuntimeError):
    """Raised when an automated test or destructive operation is attempted on an unsafe database."""


test_engine: AsyncEngine = create_async_engine(
    settings.test_database_url,
    poolclass=NullPool,
    future=True,
)

TestAsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

_init_lock = asyncio.Lock()
_test_db_initialized = False


def get_expected_test_database_name() -> str:
    """Return the expected database name parsed from the active test database URL."""
    parsed = urlparse(settings.test_database_url)
    target_db = parsed.path.lstrip("/")
    if not target_db:
        raise DatabaseSafetyViolationError(
            "Configured test_database_url does not specify a target database name."
        )
    return target_db


async def assert_test_database(session: AsyncSession) -> None:
    """Verify that the currently active session is connected to the designated test database.

    Raises DatabaseSafetyViolationError if connected to the application database (cip_db)
    or any database not intended for automated tests.
    """
    result = await session.execute(text("SELECT current_database();"))
    current_db = result.scalar()
    if not current_db:
        raise DatabaseSafetyViolationError(
            "Safety guard error: Unable to determine currently connected PostgreSQL database."
        )

    # 1. Hard check against application database
    if current_db == settings.postgres_db:
        raise DatabaseSafetyViolationError(
            f"Safety guard triggered: Connected to application database '{current_db}'! "
            f"Automated test execution and destructive operations on '{settings.postgres_db}' "
            f"are strictly forbidden to protect development and historical data."
        )

    # 2. Check against expected test database name
    expected_db = get_expected_test_database_name()
    if current_db != expected_db:
        raise DatabaseSafetyViolationError(
            f"Safety guard triggered: Connected to database '{current_db}', "
            f"but expected designated test database '{expected_db}'."
        )


async def safe_truncate_test_tables(session: AsyncSession, tables: list[str]) -> None:
    """Safely truncate specified tables only after verifying the connection is to the test database.

    Raises DatabaseSafetyViolationError if the connected database is unsafe.
    """
    await assert_test_database(session)
    for table in tables:
        safe_name = table.strip().replace(";", "").replace('"', "")
        await session.execute(text(f'TRUNCATE TABLE "{safe_name}" CASCADE;'))
    await session.commit()


def _run_alembic_upgrade_head() -> None:
    """Execute Alembic migration to head against the test database."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ini_path = os.path.join(base_dir, "alembic.ini")
    alembic_cfg = Config(ini_path)
    alembic_cfg.set_main_option("sqlalchemy.url", settings.test_database_url)
    command.upgrade(alembic_cfg, "head")


async def ensure_test_database_exists() -> None:
    """Verify that the test database exists on the PostgreSQL server, creating it if absent."""
    target_db = get_expected_test_database_name()

    # Maintenance connection parameters: connect to maintenance db ("postgres" or default)
    # Using asyncpg directly avoids creating SQLAlchemy engine pools for DDL
    maintenance_db = "postgres" if settings.postgres_db != "postgres" else "template1"
    try:
        conn = await asyncpg.connect(
            user=settings.postgres_user,
            password=settings.postgres_password,
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=maintenance_db,
        )
    except Exception:
        # Fall back to connecting to settings.postgres_db as maintenance connection if "postgres" db is unavailable
        conn = await asyncpg.connect(
            user=settings.postgres_user,
            password=settings.postgres_password,
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.postgres_db,
        )

    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1;", target_db
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{target_db}" OWNER "{settings.postgres_user}";')
    finally:
        await conn.close()


async def init_test_database() -> None:
    """Ensure the test database exists, is migrated to Alembic head, and has reference data seeded."""
    global _test_db_initialized
    if _test_db_initialized:
        return

    async with _init_lock:
        if _test_db_initialized:
            return

        # 1. Create database if it does not exist
        await ensure_test_database_exists()

        # 2. Run Alembic migrations to head in a separate thread to avoid event loop conflicts
        await asyncio.to_thread(_run_alembic_upgrade_head)

        # 3. Initialize canonical reference data (plans and platform features)
        async with TestAsyncSessionLocal() as session:
            await assert_test_database(session)
            await initialize_reference_data(session)

        _test_db_initialized = True
