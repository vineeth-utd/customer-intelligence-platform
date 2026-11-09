from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import uuid

import pytest
from sqlalchemy import delete, text

from app.db.session import AsyncSessionLocal, engine
from app.models.merchant import Merchant
from app.services.dashboard import (
    get_merchant_dashboard,
    get_platform_dashboard,
)


@pytest.fixture
async def session():
    await engine.dispose()
    s = AsyncSessionLocal()
    try:
        await s.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"Database unavailable: {exc}")

    yield s
    await s.rollback()
    await s.close()
    await engine.dispose()


@pytest.fixture
async def setup_merchant(session):
    merchant_id = uuid.uuid4()
    now_utc = datetime.now(timezone.utc)
    base_date = now_utc.date()

    merchant = Merchant(
        merchant_id=merchant_id,
        shopify_store_id=f"shop-dashboard-{merchant_id.hex[:8]}.myshopify.com",
        merchant_name="Dashboard Store",
        email=f"dash-{merchant_id.hex[:8]}@test.com",
        country="US",
        timezone="UTC",
        store_currency="USD",
        app_install_status="installed",
        created_at=now_utc - timedelta(days=30),
    )
    session.add(merchant)
    await session.commit()

    yield {
        "merchant_id": merchant_id,
        "base_date": base_date,
    }

    await session.execute(delete(Merchant).where(Merchant.merchant_id == merchant_id))
    await session.commit()


@pytest.mark.asyncio
async def test_get_platform_dashboard_success(session):
    start = date(2026, 1, 1)
    end = date(2026, 1, 31)

    result = await get_platform_dashboard(session, start, end)
    assert result is not None
    assert result.summary is not None
    assert isinstance(result.trends, list)
    assert isinstance(result.features, list)


@pytest.mark.asyncio
async def test_get_platform_dashboard_invalid_dates(session):
    with pytest.raises(ValueError, match="start_date cannot be after end_date"):
        await get_platform_dashboard(session, date(2026, 2, 1), date(2026, 1, 1))


@pytest.mark.asyncio
async def test_get_merchant_dashboard_success(session, setup_merchant):
    ctx = setup_merchant
    merchant_id = ctx["merchant_id"]
    base_date = ctx["base_date"]
    start = base_date - timedelta(days=30)
    end = base_date

    result = await get_merchant_dashboard(session, merchant_id, start, end)
    assert result is not None
    assert result.merchant_id == merchant_id
    assert result.merchant.merchant_name == "Dashboard Store"
    assert result.revenue is not None
    assert result.funnel is not None
    assert result.journeys is not None
    assert result.behavior is not None
    assert isinstance(result.campaigns, list)


@pytest.mark.asyncio
async def test_get_merchant_dashboard_non_existent_merchant(session):
    missing_id = uuid.uuid4()
    start = date(2026, 1, 1)
    end = date(2026, 1, 31)

    result = await get_merchant_dashboard(session, missing_id, start, end)
    assert result is None

