import json
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from app.kafka.consumer import ProductEventConsumer
from app.schemas.events.envelope import ProductEventEnvelope
from app.schemas.events.event_types import ProductEventType
from app.schemas.events.payloads.product import ProductCreatedPayload


@dataclass
class _FakeMessage:
    value: bytes
    topic: str = "cip.product.events"
    partition: int = 0
    offset: int = 0


def _valid_envelope() -> ProductEventEnvelope:
    return ProductEventEnvelope(
        event_id=uuid4(),
        event_type=ProductEventType.PRODUCT_CREATED,
        event_version=1,
        event_timestamp=datetime.now(timezone.utc),
        merchant_id=uuid4(),
        product_id=uuid4(),
        payload=ProductCreatedPayload(product_name="Trail Runner", category="Footwear", status="active").model_dump(
            mode="json"
        ),
        source="test",
    )


def test_validate_accepts_a_well_formed_envelope_and_payload():
    consumer = ProductEventConsumer()
    envelope = _valid_envelope()
    message = _FakeMessage(value=envelope.model_dump_json().encode("utf-8"))

    assert consumer._validate(message) == envelope


def test_validate_rejects_malformed_json():
    consumer = ProductEventConsumer()
    message = _FakeMessage(value=b"not json")

    assert consumer._validate(message) is None


def test_validate_rejects_unknown_event_type():
    consumer = ProductEventConsumer()
    raw = _valid_envelope().model_dump(mode="json")
    raw["event_type"] = "not_a_real_event_type"
    message = _FakeMessage(value=json.dumps(raw).encode("utf-8"))

    assert consumer._validate(message) is None


def test_validate_rejects_unregistered_event_version():
    consumer = ProductEventConsumer()
    raw = _valid_envelope().model_dump(mode="json")
    raw["event_version"] = 99
    message = _FakeMessage(value=json.dumps(raw).encode("utf-8"))

    assert consumer._validate(message) is None


def test_validate_rejects_payload_that_does_not_match_registered_schema():
    consumer = ProductEventConsumer()
    raw = _valid_envelope().model_dump(mode="json")
    raw["payload"] = {"unexpected_field": "value"}
    message = _FakeMessage(value=json.dumps(raw).encode("utf-8"))

    assert consumer._validate(message) is None
