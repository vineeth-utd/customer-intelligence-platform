import pytest
from pydantic import BaseModel

from app.schemas.events.registry import get_payload_schema, register_event_payload


def test_register_and_lookup_round_trip():
    @register_event_payload("TEST_EVENT_REGISTER_LOOKUP", 1)
    class _DummyPayload(BaseModel):
        note: str

    resolved = get_payload_schema("TEST_EVENT_REGISTER_LOOKUP", 1)
    assert resolved is _DummyPayload


def test_duplicate_registration_raises():
    @register_event_payload("TEST_EVENT_DUPLICATE", 1)
    class _First(BaseModel):
        pass

    with pytest.raises(ValueError):

        @register_event_payload("TEST_EVENT_DUPLICATE", 1)
        class _Second(BaseModel):
            pass


def test_unregistered_lookup_returns_none():
    assert get_payload_schema("TEST_EVENT_NEVER_REGISTERED", 1) is None
