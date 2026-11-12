"""Tests verifying test database isolation, safety guards, and destructive operation rejection.

Proves that:
1. Destructive operations (truncate) are strictly rejected against the application database (cip_db).
2. Database safety assertions fail fast if any session connects to cip_db or an unexpected database.
3. Safe operations succeed within the dedicated cip_test_db.
4. Settings validation prevents configuring tests against cip_db or missing test DB names.
5. Explicit TEST_DATABASE_URL overrides are supported and checked for safety.
"""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config.settings import Settings, settings
from tests.database import (
    DatabaseSafetyViolationError,
    TestAsyncSessionLocal,
    assert_test_database,
    safe_truncate_test_tables,
)


@pytest.mark.asyncio
async def test_assert_test_database_rejects_application_database():
    """Verify that assert_test_database immediately raises if connected to cip_db."""
    app_engine = create_async_engine(settings.database_url, poolclass=NullPool)
    app_session_maker = async_sessionmaker(bind=app_engine, class_=AsyncSession)
    try:
        async with app_session_maker() as session:
            with pytest.raises(DatabaseSafetyViolationError) as exc_info:
                await assert_test_database(session)
            assert "cip_db" in str(exc_info.value)
            assert "strictly forbidden" in str(exc_info.value)
    finally:
        await app_engine.dispose()


@pytest.mark.asyncio
async def test_safe_truncate_rejects_application_database():
    """Verify that safe_truncate_test_tables refuses to truncate when connected to cip_db."""
    app_engine = create_async_engine(settings.database_url, poolclass=NullPool)
    app_session_maker = async_sessionmaker(bind=app_engine, class_=AsyncSession)
    try:
        async with app_session_maker() as session:
            with pytest.raises(DatabaseSafetyViolationError) as exc_info:
                await safe_truncate_test_tables(session, ["merchants"])
            assert "cip_db" in str(exc_info.value)
    finally:
        await app_engine.dispose()


@pytest.mark.asyncio
async def test_assert_test_database_succeeds_on_test_db(db_session: AsyncSession):
    """Verify that assert_test_database passes on cip_test_db."""
    # db_session is connected to cip_test_db
    await assert_test_database(db_session)
    result = await db_session.execute(text("SELECT current_database();"))
    current_db = result.scalar()
    assert current_db == settings.postgres_test_db


@pytest.mark.asyncio
async def test_safe_truncate_succeeds_on_test_db(db_session: AsyncSession):
    """Verify that safe_truncate_test_tables succeeds when operating on cip_test_db."""
    await safe_truncate_test_tables(db_session, ["platform_events"])


def test_settings_validation_rejects_identical_databases():
    """Verify that Settings rejects configuring postgres_test_db == postgres_db."""
    with pytest.raises(ValueError) as exc_info:
        Settings(postgres_test_db="cip_db")
    assert "cannot be identical to postgres_db" in str(exc_info.value)


def test_settings_validation_rejects_empty_test_db():
    """Verify that Settings rejects empty postgres_test_db."""
    with pytest.raises(ValueError) as exc_info:
        Settings(postgres_test_db="   ")
    assert "postgres_test_db must not be empty" in str(exc_info.value)


def test_settings_validation_rejects_test_database_url_pointing_to_cip_db():
    """Verify that Settings rejects test_database_url override pointing to cip_db."""
    with pytest.raises(ValueError) as exc_info:
        Settings(test_database_url="postgresql+asyncpg://cip_user:cip_password@localhost:5433/cip_db")
    assert "test_database_url points to the application database" in str(exc_info.value)


def test_settings_supports_explicit_test_database_url_override():
    """Verify that Settings supports an explicit custom TEST_DATABASE_URL."""
    custom_url = "postgresql+asyncpg://cip_user:cip_password@localhost:5433/custom_ci_test_db"
    custom_settings = Settings(test_database_url=custom_url)
    assert custom_settings.test_database_url == custom_url


@pytest.mark.asyncio
async def test_assert_test_database_rejects_mismatched_test_db_override():
    """Verify that if an override is configured, the connected DB must match the override."""
    # Mock settings.test_database_url to expect 'other_test_db'
    mock_url = "postgresql+asyncpg://cip_user:cip_password@localhost:5433/other_test_db"
    with patch.object(settings, "test_database_url_override", mock_url):
        async with TestAsyncSessionLocal() as session:
            with pytest.raises(DatabaseSafetyViolationError) as exc_info:
                await assert_test_database(session)
            assert "expected designated test database 'other_test_db'" in str(exc_info.value)
