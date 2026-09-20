import json
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from app.kafka.consumer import ShopperEventConsumer
from app.schemas.events.envelope import ShopperEventEnvelope
from app.schemas.events.event_types import ShopperEventType
from app.schemas.events.payloads.shopper import SessionStartedPayload


@dataclass
class _FakeMessage:
    value: bytes
    topic: str = "cip.shopper.events"
    partition: int = 0
    offset: int = 0


def _valid_envelope() -> ShopperEventEnvelope:
    return ShopperEventEnvelope(
        event_id=uuid4(),
        event_type=ShopperEventType.SESSION_STARTED,
        event_version=1,
        event_timestamp=datetime.now(timezone.utc),
        merchant_id=uuid4(),
        shopper_id=uuid4(),
        session_id=uuid4(),
        payload=SessionStartedPayload(referrer="google.com", email=None).model_dump(
            mode="json"
        ),
        source="test",
    )


def test_validate_accepts_a_well_formed_envelope_and_payload():
    consumer = ShopperEventConsumer()
    envelope = _valid_envelope()
    message = _FakeMessage(value=envelope.model_dump_json().encode("utf-8"))

    assert consumer._validate(message) == envelope


def test_validate_rejects_malformed_json():
    consumer = ShopperEventConsumer()
    message = _FakeMessage(value=b"not json")

    assert consumer._validate(message) is None


def test_validate_rejects_unknown_event_type():
    consumer = ShopperEventConsumer()
    raw = _valid_envelope().model_dump(mode="json")
    raw["event_type"] = "not_a_real_event_type"
    message = _FakeMessage(value=json.dumps(raw).encode("utf-8"))

    assert consumer._validate(message) is None


def test_validate_rejects_unregistered_event_version():
    consumer = ShopperEventConsumer()
    raw = _valid_envelope().model_dump(mode="json")
    raw["event_version"] = 99
    message = _FakeMessage(value=json.dumps(raw).encode("utf-8"))

    assert consumer._validate(message) is None


def test_validate_rejects_payload_that_does_not_match_registered_schema():
    consumer = ShopperEventConsumer()
    raw = _valid_envelope().model_dump(mode="json")
    raw["event_type"] = "ADD_TO_CART" # Has required fields: product_id, variant_id, quantity, unit_price
    raw["payload"] = {"unexpected_field": "value"}
    message = _FakeMessage(value=json.dumps(raw).encode("utf-8"))

    assert consumer._validate(message) is None
