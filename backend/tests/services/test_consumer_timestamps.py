"""Unit tests for operational timestamp persistence in consumer handlers and DAL."""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest

from app.data_access.campaign import create_campaign
from app.data_access.merchant import create_merchant
from app.data_access.order import create_order
from app.data_access.product import create_product, create_product_variant
from app.data_access.shopper import upsert_shopper
from app.schemas.events.envelope import (
    CampaignEventEnvelope,
    MerchantEventEnvelope,
    ProductEventEnvelope,
)
from app.schemas.events.event_types import (
    CampaignEventType,
    MerchantEventType,
    ProductEventType,
)
from app.services.campaign import _handle_campaign_created
from app.services.merchant import _handle_merchant_created
from app.services.product import _handle_product_created, _handle_product_variant_created


@pytest.mark.asyncio
async def test_create_merchant_passes_created_at_to_insert():
    session = AsyncMock()
    m_id = uuid.uuid4()
    historical_time = datetime(2026, 9, 15, 12, 0, 0, tzinfo=timezone.utc)

    await create_merchant(
        session,
        merchant_id=m_id,
        shopify_store_id="store-1",
        merchant_name="Store One",
        email="store@example.com",
        country="US",
        timezone="America/New_York",
        store_currency="USD",
        app_install_status="pending_install",
        created_at=historical_time,
    )

    assert session.execute.called
    stmt = session.execute.call_args[0][0]
    # Verify values dictionary in the statement contains created_at
    compiled_params = stmt.compile().params
    assert compiled_params["created_at"] == historical_time
    assert compiled_params["merchant_id"] == m_id


@pytest.mark.asyncio
async def test_handle_merchant_created_passes_event_timestamp():
    session = AsyncMock()
    m_id = uuid.uuid4()
    historical_time = datetime(2026, 9, 15, 14, 30, 0, tzinfo=timezone.utc)

    envelope = MerchantEventEnvelope(
        event_id=uuid.uuid4(),
        merchant_id=m_id,
        event_type=MerchantEventType.MERCHANT_CREATED,
        event_version=1,
        event_timestamp=historical_time,
        source="test",
        payload={
            "shopify_store_id": "store-xyz",
            "merchant_name": "Test Merchant",
            "email": "merchant@example.com",
            "country": "US",
            "timezone": "America/New_York",
            "store_currency": "USD",
        },
    )

    with patch("app.services.merchant.create_merchant", new_callable=AsyncMock) as mock_create:
        await _handle_merchant_created(session, envelope)
        mock_create.assert_called_once_with(
            session,
            merchant_id=m_id,
            shopify_store_id="store-xyz",
            merchant_name="Test Merchant",
            email="merchant@example.com",
            country="US",
            timezone="America/New_York",
            store_currency="USD",
            app_install_status="pending_install",
            created_at=historical_time,
        )


@pytest.mark.asyncio
async def test_create_product_and_variant_passes_created_at():
    session = AsyncMock()
    p_id = uuid.uuid4()
    m_id = uuid.uuid4()
    v_id = uuid.uuid4()
    t_prod = datetime(2026, 9, 16, 10, 0, 0, tzinfo=timezone.utc)
    t_var = datetime(2026, 9, 16, 10, 5, 0, tzinfo=timezone.utc)

    await create_product(
        session,
        product_id=p_id,
        merchant_id=m_id,
        product_name="Historical Widget",
        category="Widgets",
        vendor="WidgetCo",
        status="active",
        created_at=t_prod,
    )
    stmt_prod = session.execute.call_args[0][0]
    assert stmt_prod.compile().params["created_at"] == t_prod

    await create_product_variant(
        session,
        variant_id=v_id,
        product_id=p_id,
        variant_name="Small Widget",
        sku="WID-SM",
        price=Decimal("19.99"),
        size="S",
        color="Blue",
        inventory_quantity=50,
        status="active",
        created_at=t_var,
    )
    stmt_var = session.execute.call_args[0][0]
    assert stmt_var.compile().params["created_at"] == t_var


@pytest.mark.asyncio
async def test_handle_product_events_pass_event_timestamp():
    session = AsyncMock()
    m_id = uuid.uuid4()
    p_id = uuid.uuid4()
    v_id = uuid.uuid4()
    t_event = datetime(2026, 9, 16, 11, 0, 0, tzinfo=timezone.utc)

    envelope_prod = ProductEventEnvelope(
        event_id=uuid.uuid4(),
        merchant_id=m_id,
        product_id=p_id,
        event_type=ProductEventType.PRODUCT_CREATED,
        event_version=1,
        event_timestamp=t_event,
        source="test",
        payload={
            "product_name": "Test Shirt",
            "category": "Apparel",
            "vendor": "Acme",
            "status": "active",
        },
    )

    with patch("app.services.product.create_product", new_callable=AsyncMock) as mock_create_prod:
        await _handle_product_created(session, envelope_prod)
        mock_create_prod.assert_called_once_with(
            session,
            product_id=p_id,
            merchant_id=m_id,
            product_name="Test Shirt",
            category="Apparel",
            vendor="Acme",
            status="active",
            created_at=t_event,
        )

    envelope_var = ProductEventEnvelope(
        event_id=uuid.uuid4(),
        merchant_id=m_id,
        product_id=p_id,
        event_type=ProductEventType.PRODUCT_VARIANT_CREATED,
        event_version=1,
        event_timestamp=t_event,
        source="test",
        payload={
            "variant_id": str(v_id),
            "variant_name": "Large Shirt",
            "sku": "SHIRT-LG",
            "price": 29.99,
            "size": "L",
            "color": "Green",
            "inventory_quantity": 25,
            "status": "active",
        },
    )

    with patch("app.services.product.create_product_variant", new_callable=AsyncMock) as mock_create_var:
        await _handle_product_variant_created(session, envelope_var)
        mock_create_var.assert_called_once()
        _, kwargs = mock_create_var.call_args
        assert kwargs["created_at"] == t_event
        assert kwargs["variant_id"] == v_id


@pytest.mark.asyncio
async def test_upsert_shopper_preserves_first_seen_at_and_created_at():
    session = AsyncMock()
    mock_result = MagicMock()
    mock_shopper = MagicMock()
    mock_result.scalar_one.return_value = mock_shopper
    session.execute.return_value = mock_result

    m_id = uuid.uuid4()
    s_id = uuid.uuid4()
    t_first = datetime(2026, 9, 14, 8, 0, 0, tzinfo=timezone.utc)

    shopper = await upsert_shopper(session, m_id, s_id, t_first)
    assert shopper == mock_shopper

    stmt = session.execute.call_args[0][0]
    compiled_params = stmt.compile().params
    assert compiled_params["first_seen_at"] == t_first
    assert compiled_params["last_seen_at"] == t_first
    assert compiled_params["created_at"] == t_first


@pytest.mark.asyncio
async def test_create_campaign_passes_created_at():
    session = AsyncMock()
    c_id = uuid.uuid4()
    m_id = uuid.uuid4()
    seg_id = uuid.uuid4()
    t_camp = datetime(2026, 9, 20, 9, 0, 0, tzinfo=timezone.utc)

    campaign = await create_campaign(
        session,
        campaign_id=c_id,
        merchant_id=m_id,
        segment_id=seg_id,
        campaign_name="Fall Promo",
        campaign_type="promotional",
        campaign_medium="email",
        status="active",
        start_at=t_camp,
        end_at=None,
        created_at=t_camp,
    )

    assert campaign.campaign_id == c_id
    assert campaign.created_at == t_camp
    assert session.add.called


@pytest.mark.asyncio
async def test_create_order_sets_created_at_to_placed_at():
    session = AsyncMock()
    o_id = uuid.uuid4()
    m_id = uuid.uuid4()
    s_id = uuid.uuid4()
    t_placed = datetime(2026, 9, 25, 16, 45, 0, tzinfo=timezone.utc)

    order = await create_order(
        session,
        order_id=o_id,
        merchant_id=m_id,
        shopper_id=s_id,
        currency="USD",
        total_amount=99.50,
        placed_at=t_placed,
        completed_at=t_placed,
    )

    assert order.order_id == o_id
    assert order.placed_at == t_placed
    assert order.created_at == t_placed
    assert session.add.called

