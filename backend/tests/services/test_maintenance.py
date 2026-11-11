"""Unit tests for synthetic data reset and reference data survival."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.maintenance import SYNTHETIC_TABLES, reset_synthetic_data


@pytest.mark.asyncio
async def test_reset_synthetic_data_truncates_synthetic_tables_and_reinitializes_reference():
    session = AsyncMock()
    session.scalar.side_effect = [3, 10] # plans_count = 3, features_count = 10

    with (
        patch("app.services.maintenance.initialize_reference_data", new_callable=AsyncMock) as mock_init_ref,
        patch("app.services.maintenance.refresh_aggregate_views", new_callable=AsyncMock) as mock_refresh,
    ):
        await reset_synthetic_data(session)

        # 1. Truncate was executed
        assert session.execute.called
        sql_stmt = str(session.execute.call_args[0][0])
        assert "TRUNCATE TABLE" in sql_stmt
        for table in SYNTHETIC_TABLES:
            assert f'"{table}"' in sql_stmt
        assert session.commit.called

        # 2. Reference data was re-initialized
        mock_init_ref.assert_called_once_with(session)

        # 3. Materialized views were refreshed
        mock_refresh.assert_called_once_with(session)

