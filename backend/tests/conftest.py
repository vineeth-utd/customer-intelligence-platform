"""Root pytest configuration and shared fixtures for the test suite.

Provides isolated test database sessions and engines pointing strictly to
cip_test_db, preventing any automated test from accessing or mutating the
application database (cip_db).
"""

from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

import app.db.session as app_db_session
from app.config.settings import settings
from tests.database import (
    TestAsyncSessionLocal,
    assert_test_database,
    init_test_database,
    test_engine,
)

# Bind application sessionmaker and engine to dedicated test database for automated tests
app_db_session.AsyncSessionLocal = TestAsyncSessionLocal
app_db_session.engine = test_engine


@pytest.fixture(scope="session")
async def test_db_initialized() -> bool:
    """Ensure the dedicated test database is created, migrated, and seeded.

    Lazy initialization: only runs when a test explicitly requests a database fixture,
    keeping pure unit tests fast and independent of PostgreSQL.
    """
    try:
        await init_test_database()
    except Exception as exc:
        pytest.skip(
            f"Test PostgreSQL is not reachable at {settings.postgres_host}:{settings.postgres_port}: {exc}"
        )
    return True


@pytest.fixture
def isolate_test_db(test_db_initialized: bool):
    """Patch application-level AsyncSessionLocal and engine to the test DB for the duration of the test.

    Ensures background consumers, schedulers, and services that create sessions internally
    operate strictly within cip_test_db.
    """
    with patch.object(app_db_session, "AsyncSessionLocal", TestAsyncSessionLocal), \
         patch.object(app_db_session, "engine", test_engine):
        yield


@pytest.fixture
async def db_session(isolate_test_db) -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated AsyncSession bound strictly to cip_test_db."""
    async with TestAsyncSessionLocal() as session:
        await assert_test_database(session)
        yield session
        await session.rollback()


@pytest.fixture
def test_engine_fixture(isolate_test_db) -> AsyncEngine:
    """Provide the dedicated test engine."""
    return test_engine


@pytest.fixture
def test_session_factory(isolate_test_db) -> async_sessionmaker[AsyncSession]:
    """Provide the dedicated test sessionmaker."""
    return TestAsyncSessionLocal
