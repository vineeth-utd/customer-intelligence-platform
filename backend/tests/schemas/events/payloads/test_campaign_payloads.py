import uuid
from decimal import Decimal

from app.schemas.events.event_types import CampaignEventType
from app.schemas.events.payloads.campaign import (
    AdClickedPayload,
    AdViewedPayload,
    CampaignConvertedPayload,
    CampaignCreatedPayload,
    CampaignUpdatedPayload,
    EmailClickedPayload,
    EmailDeliveredPayload,
    EmailOpenedPayload,
    PushDeliveredPayload,
    PushOpenedPayload,
    SmsClickedPayload,
    SmsDeliveredPayload,
)
from app.schemas.events.registry import get_payload_schema


def test_campaign_created_payload():
    schema = get_payload_schema(CampaignEventType.CAMPAIGN_CREATED.value, 1)
    assert schema == CampaignCreatedPayload

    segment_id = uuid.uuid4()
    payload = CampaignCreatedPayload(
        campaign_name="Test Campaign",
        campaign_type="Promotional",
        campaign_medium="Email",
        segment_id=segment_id,
        status="DRAFT"
    )
    assert payload.campaign_name == "Test Campaign"


def test_campaign_updated_payload():
    schema = get_payload_schema(CampaignEventType.CAMPAIGN_UPDATED.value, 1)
    assert schema == CampaignUpdatedPayload

    payload = CampaignUpdatedPayload(changed_values={"status": "ACTIVE"})
    assert payload.changed_values == {"status": "ACTIVE"}


def test_email_events():
    assert get_payload_schema(CampaignEventType.EMAIL_DELIVERED.value, 1) == EmailDeliveredPayload
    assert get_payload_schema(CampaignEventType.EMAIL_OPENED.value, 1) == EmailOpenedPayload
    assert get_payload_schema(CampaignEventType.EMAIL_CLICKED.value, 1) == EmailClickedPayload

    delivered = EmailDeliveredPayload()
    opened = EmailOpenedPayload()
    clicked = EmailClickedPayload(url="https://example.com/promo")
    assert clicked.url == "https://example.com/promo"


def test_sms_events():
    assert get_payload_schema(CampaignEventType.SMS_DELIVERED.value, 1) == SmsDeliveredPayload
    assert get_payload_schema(CampaignEventType.SMS_CLICKED.value, 1) == SmsClickedPayload

    delivered = SmsDeliveredPayload()
    clicked = SmsClickedPayload(url="https://example.com/promo")
    assert clicked.url == "https://example.com/promo"


def test_push_events():
    assert get_payload_schema(CampaignEventType.PUSH_DELIVERED.value, 1) == PushDeliveredPayload
    assert get_payload_schema(CampaignEventType.PUSH_OPENED.value, 1) == PushOpenedPayload

    delivered = PushDeliveredPayload()
    opened = PushOpenedPayload(action="view_sale")
    assert opened.action == "view_sale"


def test_ad_events():
    assert get_payload_schema(CampaignEventType.AD_VIEWED.value, 1) == AdViewedPayload
    assert get_payload_schema(CampaignEventType.AD_CLICKED.value, 1) == AdClickedPayload

    viewed = AdViewedPayload()
    clicked = AdClickedPayload(url="https://example.com/promo")
    assert clicked.url == "https://example.com/promo"


def test_campaign_converted_payload():
    schema = get_payload_schema(CampaignEventType.CAMPAIGN_CONVERTED.value, 1)
    assert schema == CampaignConvertedPayload

    order_id = uuid.uuid4()
    payload = CampaignConvertedPayload(order_id=order_id)
    assert payload.order_id == order_id
