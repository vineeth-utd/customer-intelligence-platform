import base64
from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.events.dlq import DeadLetterRecord


def test_dlq_record_accepts_valid_metadata():
    record = DeadLetterRecord(
        original_topic="my.topic",
        original_partition=0,
        original_offset=100,
        consumer_group_id="my-group",
        failure_stage="validation",
        error_type="ValidationError",
        error_message="Invalid data",
        failed_at=datetime.now(timezone.utc),
        original_message_base64="aGVsbG8=",
        original_event_id=uuid4(),
        event_type="MY_EVENT",
    )
    assert record.original_topic == "my.topic"
    assert record.failure_stage == "validation"


def test_dlq_record_optional_fields():
    record = DeadLetterRecord(
        original_topic="my.topic",
        original_partition=0,
        original_offset=100,
        consumer_group_id="my-group",
        failure_stage="processing",
        error_type="RuntimeError",
        error_message="Boom",
        failed_at=datetime.now(timezone.utc),
        original_message_base64="aGVsbG8=",
    )
    assert record.original_event_id is None
    assert record.event_type is None


def test_dlq_record_base64_roundtrip_with_non_utf8():
    # Intentionally use invalid UTF-8 bytes to ensure we don't break on decode
    raw_bytes = b"\xff\xfe\x00\x01\x02\x03\x04\x05\x06hello"
    b64_str = base64.b64encode(raw_bytes).decode("ascii")

    record = DeadLetterRecord(
        original_topic="my.topic",
        original_partition=0,
        original_offset=100,
        consumer_group_id="my-group",
        failure_stage="validation",
        error_type="TestError",
        error_message="Non-utf8 bytes",
        failed_at=datetime.now(timezone.utc),
        original_message_base64=b64_str,
    )

    assert base64.b64decode(record.original_message_base64) == raw_bytes

