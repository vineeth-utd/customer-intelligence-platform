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
from app.kafka.producer import EventProducer
from tests.database import (
    TestAsyncSessionLocal,
    assert_test_database,
    init_test_database,
    test_engine,
)
from tests.kafka_safety import (
    assert_test_kafka_topic,
    ensure_test_kafka_topics,
)

# 1. Bind application sessionmaker and engine to dedicated test database for automated tests
app_db_session.AsyncSessionLocal = TestAsyncSessionLocal
app_db_session.engine = test_engine

# 2. Switch Kafka topic and consumer group configurations to isolated test targets
settings.configure_test_kafka()

# 3. Patch EventProducer with a hard safety guard against publishing to development topics
_orig_publish = EventProducer.publish
_orig_publish_record = EventProducer.publish_record


async def _guarded_publish(self, topic: str, envelope, key: str | None = None) -> None:
    assert_test_kafka_topic(topic)
    return await _orig_publish(self, topic, envelope, key=key)


async def _guarded_publish_record(self, topic: str, record) -> None:
    assert_test_kafka_topic(topic)
    return await _orig_publish_record(self, topic, record)


EventProducer.publish = _guarded_publish
EventProducer.publish_record = _guarded_publish_record


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


@pytest.fixture(scope="session", autouse=True)
async def test_kafka_initialized() -> bool:
    """Ensure dedicated isolated test Kafka topics exist before running tests."""
    try:
        await ensure_test_kafka_topics()
    except Exception:
        # Kafka broker may not be running in pure unit-test runs; smoke tests skip individually
        pass
    return True
