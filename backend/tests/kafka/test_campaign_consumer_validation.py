import json
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from app.kafka.consumer import CampaignEventConsumer
from app.schemas.events.envelope import CampaignEventEnvelope
from app.schemas.events.event_types import CampaignEventType
from app.schemas.events.payloads.campaign import CampaignCreatedPayload


@dataclass
class _FakeMessage:
    value: bytes
    topic: str = "cip.campaign.events"
    partition: int = 0
    offset: int = 0


def _valid_envelope() -> CampaignEventEnvelope:
    return CampaignEventEnvelope(
        event_id=uuid4(),
        event_type=CampaignEventType.CAMPAIGN_CREATED,
        event_version=1,
        event_timestamp=datetime.now(timezone.utc),
        merchant_id=uuid4(),
        campaign_id=uuid4(),
        shopper_id=None,
        payload=CampaignCreatedPayload(
            campaign_name="Summer Launch",
            campaign_type="promotional",
            campaign_medium="email",
            segment_id=uuid4(),
            status="draft",
        ).model_dump(mode="json"),
        source="test",
    )


def test_validate_accepts_a_well_formed_envelope_and_payload():
    consumer = CampaignEventConsumer()
    envelope = _valid_envelope()
    message = _FakeMessage(value=envelope.model_dump_json().encode("utf-8"))

    assert consumer._validate(message) == envelope


def test_validate_rejects_malformed_json():
    consumer = CampaignEventConsumer()
    message = _FakeMessage(value=b"not json")

    assert consumer._validate(message) is None


def test_validate_rejects_unknown_event_type():
    consumer = CampaignEventConsumer()
    raw = _valid_envelope().model_dump(mode="json")
    raw["event_type"] = "not_a_real_event_type"
    message = _FakeMessage(value=json.dumps(raw).encode("utf-8"))

    assert consumer._validate(message) is None


def test_validate_rejects_unregistered_event_version():
    consumer = CampaignEventConsumer()
    raw = _valid_envelope().model_dump(mode="json")
    raw["event_version"] = 99
    message = _FakeMessage(value=json.dumps(raw).encode("utf-8"))

    assert consumer._validate(message) is None


def test_validate_rejects_payload_that_does_not_match_registered_schema():
    consumer = CampaignEventConsumer()
    raw = _valid_envelope().model_dump(mode="json")
    raw["payload"] = {"unexpected_field": "value"}
    message = _FakeMessage(value=json.dumps(raw).encode("utf-8"))

    assert consumer._validate(message) is None
