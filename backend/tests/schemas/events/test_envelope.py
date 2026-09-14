from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.events.envelope import MerchantEventEnvelope
from app.schemas.events.event_types import MerchantEventType


def _valid_fields() -> dict:
    return {
        "event_id": uuid4(),
        "event_type": MerchantEventType.MERCHANT_CREATED,
        "event_version": 1,
        "event_timestamp": datetime.now(timezone.utc),
        "merchant_id": uuid4(),
        "payload": {"plan": "starter"},
        "source": "generator",
    }


def test_valid_envelope_constructs():
    envelope = MerchantEventEnvelope(**_valid_fields())
    assert envelope.event_type is MerchantEventType.MERCHANT_CREATED


def test_naive_timestamp_rejected():
    fields = _valid_fields()
    fields["event_timestamp"] = datetime.now()
    with pytest.raises(ValidationError):
        MerchantEventEnvelope(**fields)


def test_missing_event_id_rejected():
    fields = _valid_fields()
    del fields["event_id"]
    with pytest.raises(ValidationError):
        MerchantEventEnvelope(**fields)


def test_missing_event_version_rejected():
    fields = _valid_fields()
    del fields["event_version"]
    with pytest.raises(ValidationError):
        MerchantEventEnvelope(**fields)


def test_invalid_event_type_rejected():
    fields = _valid_fields()
    fields["event_type"] = "NOT_A_REAL_EVENT_TYPE"
    with pytest.raises(ValidationError):
        MerchantEventEnvelope(**fields)


def test_json_round_trip_shape():
    envelope = MerchantEventEnvelope(**_valid_fields())
    dumped = envelope.model_dump(mode="json")
    assert set(dumped.keys()) == {
        "event_id",
        "event_version",
        "event_timestamp",
        "payload",
        "source",
        "event_type",
        "merchant_id",
    }
    assert isinstance(dumped["event_id"], str)
