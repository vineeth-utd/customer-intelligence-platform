import base64
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from dataclasses import dataclass

from aiokafka.structs import ConsumerRecord

from app.kafka.consumer import BaseEventConsumer
from app.schemas.events.envelope import DeadLetterRecord, MerchantEventEnvelope
from app.schemas.events.event_types import MerchantEventType
from app.schemas.events.payloads.merchant import MerchantLoginPayload


@dataclass
class _FakeMessage:
    value: bytes
    topic: str = "cip.test.events"
    partition: int = 0
    offset: int = 0


class MockError(Exception):
    pass


class MockUnexpectedError(Exception):
    pass


class MockConsumer(BaseEventConsumer[MerchantEventEnvelope]):
    def __init__(
        self,
        insert_event_fn,
        get_event_fn,
        process_event_fn,
        mark_processed_fn,
        dlq_topic="cip.test.dlq",
        business_exceptions=(MockError,),
    ):
        super().__init__(
            topic="cip.test.events",
            group_id="test-group",
            envelope_model=MerchantEventEnvelope,
            insert_event_fn=insert_event_fn,
            get_event_fn=get_event_fn,
            process_event_fn=process_event_fn,
            mark_processed_fn=mark_processed_fn,
            domain_name="test",
            dlq_topic=dlq_topic,
            business_exceptions=business_exceptions,
        )

    def get_context_id(self, envelope: MerchantEventEnvelope) -> uuid.UUID:
        return envelope.merchant_id

    # For tests, we don't start the actual kafka consumer
    async def _commit_message(self, message: ConsumerRecord) -> None:
        pass


@pytest.fixture
def mock_producer():
    with patch("app.kafka.producer.event_producer.publish_record", new_callable=AsyncMock) as m:
        yield m


@pytest.fixture
def base_envelope():
    return MerchantEventEnvelope(
        event_id=uuid.uuid4(),
        event_type=MerchantEventType.MERCHANT_LOGIN,
        event_version=1,
        event_timestamp=datetime.now(timezone.utc),
        merchant_id=uuid.uuid4(),
        payload=MerchantLoginPayload(login_channel="web").model_dump(mode="json"),
        source="test",
    )


async def test_validation_failure_dlq_publish_and_commit(mock_producer):
    consumer = MockConsumer(None, None, None, None)
    
    with patch.object(consumer, "_commit_message", new_callable=AsyncMock) as commit_spy:
        message = ConsumerRecord(topic="cip.test.events", partition=0, offset=10, timestamp=0, timestamp_type=0, key=b"", value=b"invalid json", checksum=0, serialized_key_size=0, serialized_value_size=0, headers=())
        await consumer._handle_message(message)

        # DLQ published
        mock_producer.assert_called_once()
        topic, record = mock_producer.call_args[0]
        assert topic == "cip.test.dlq"
        assert record.failure_stage == "validation"
        assert record.original_message_base64 == base64.b64encode(b"invalid json").decode("ascii")
        assert record.original_event_id is None

        # Offset committed
        commit_spy.assert_called_once_with(message)


async def test_validation_failure_extracts_metadata_from_json(mock_producer):
    consumer = MockConsumer(None, None, None, None)
    
    with patch.object(consumer, "_commit_message", new_callable=AsyncMock) as commit_spy:
        event_id = str(uuid.uuid4())
        raw_json = json.dumps({"event_id": event_id, "event_type": "MERCHANT_LOGIN", "invalid": "schema"}).encode("utf-8")
        message = ConsumerRecord(topic="cip.test.events", partition=0, offset=11, timestamp=0, timestamp_type=0, key=b"", value=raw_json, checksum=0, serialized_key_size=0, serialized_value_size=0, headers=())
        await consumer._handle_message(message)

        # DLQ published
        mock_producer.assert_called_once()
        topic, record = mock_producer.call_args[0]
        assert record.failure_stage == "validation"
        assert str(record.original_event_id) == event_id
        assert record.event_type == "MERCHANT_LOGIN"

        commit_spy.assert_called_once_with(message)


async def test_validation_dlq_publication_failure_halts(mock_producer):
    consumer = MockConsumer(None, None, None, None)
    
    with patch.object(consumer, "_commit_message", new_callable=AsyncMock) as commit_spy:
        mock_producer.side_effect = RuntimeError("Kafka down")

        message = ConsumerRecord(topic="cip.test.events", partition=0, offset=12, timestamp=0, timestamp_type=0, key=b"", value=b"invalid json", checksum=0, serialized_key_size=0, serialized_value_size=0, headers=())
        
        with pytest.raises(RuntimeError, match="Kafka down"):
            await consumer._handle_message(message)

        commit_spy.assert_not_called()


async def test_business_failure_dlq_publish_and_commit(mock_producer, base_envelope):
    class AsyncMockSession:
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc_val, exc_tb): pass
        async def commit(self): pass

    async def mock_insert(*args): return True
    
    class MockEvent:
        processed = False
    async def mock_get(*args): return MockEvent()

    async def mock_process(*args): raise MockError("Business failed")
    async def mock_mark(*args): pass

    consumer = MockConsumer(mock_insert, mock_get, mock_process, mock_mark)
    
    with patch("app.kafka.consumer.AsyncSessionLocal", return_value=AsyncMockSession()), \
         patch.object(consumer, "_commit_message", new_callable=AsyncMock) as commit_spy:

        raw_json = base_envelope.model_dump_json().encode("utf-8")
        message = ConsumerRecord(topic="cip.test.events", partition=0, offset=13, timestamp=0, timestamp_type=0, key=b"", value=raw_json, checksum=0, serialized_key_size=0, serialized_value_size=0, headers=())
        
        await consumer._handle_message(message)

        mock_producer.assert_called_once()
        topic, record = mock_producer.call_args[0]
        assert record.failure_stage == "processing"
        assert record.error_type == "MockError"
        assert record.error_message == "Business failed"
        assert record.original_event_id == base_envelope.event_id
        
        commit_spy.assert_called_once_with(message)


async def test_unexpected_exception_halts_no_dlq(mock_producer, base_envelope):
    class AsyncMockSession:
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc_val, exc_tb): pass
        async def commit(self): pass

    async def mock_insert(*args): return True
    
    class MockEvent:
        processed = False
    async def mock_get(*args): return MockEvent()

    async def mock_process(*args): raise MockUnexpectedError("Infrastructure failed")
    async def mock_mark(*args): pass

    consumer = MockConsumer(mock_insert, mock_get, mock_process, mock_mark)
    
    with patch("app.kafka.consumer.AsyncSessionLocal", return_value=AsyncMockSession()), \
         patch.object(consumer, "_commit_message", new_callable=AsyncMock) as commit_spy:

        raw_json = base_envelope.model_dump_json().encode("utf-8")
        message = ConsumerRecord(topic="cip.test.events", partition=0, offset=14, timestamp=0, timestamp_type=0, key=b"", value=raw_json, checksum=0, serialized_key_size=0, serialized_value_size=0, headers=())
        
        with pytest.raises(MockUnexpectedError):
            await consumer._handle_message(message)

        mock_producer.assert_not_called()
        commit_spy.assert_not_called()


async def test_business_failure_dlq_publication_failure_halts(mock_producer, base_envelope):
    class AsyncMockSession:
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc_val, exc_tb): pass
        async def commit(self): pass

    async def mock_insert(*args): return True
    
    class MockEvent:
        processed = False
    async def mock_get(*args): return MockEvent()

    async def mock_process(*args): raise MockError("Business failed")
    async def mock_mark(*args): pass

    consumer = MockConsumer(mock_insert, mock_get, mock_process, mock_mark)
    mock_producer.side_effect = RuntimeError("Kafka down")

    with patch("app.kafka.consumer.AsyncSessionLocal", return_value=AsyncMockSession()), \
         patch.object(consumer, "_commit_message", new_callable=AsyncMock) as commit_spy:

        raw_json = base_envelope.model_dump_json().encode("utf-8")
        message = ConsumerRecord(topic="cip.test.events", partition=0, offset=15, timestamp=0, timestamp_type=0, key=b"", value=raw_json, checksum=0, serialized_key_size=0, serialized_value_size=0, headers=())
        
        with pytest.raises(RuntimeError, match="Kafka down"):
            await consumer._handle_message(message)

        commit_spy.assert_not_called()


async def test_dlq_disabled_mode_validation(mock_producer):
    consumer = MockConsumer(None, None, None, None, dlq_topic=None)
    
    with patch.object(consumer, "_commit_message", new_callable=AsyncMock) as commit_spy:
        message = ConsumerRecord(topic="cip.test.events", partition=0, offset=16, timestamp=0, timestamp_type=0, key=b"", value=b"invalid json", checksum=0, serialized_key_size=0, serialized_value_size=0, headers=())
        await consumer._handle_message(message)

        mock_producer.assert_not_called()
        commit_spy.assert_called_once_with(message)


async def test_dlq_disabled_mode_business_error(mock_producer, base_envelope):
    class AsyncMockSession:
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc_val, exc_tb): pass
        async def commit(self): pass

    async def mock_insert(*args): return True
    class MockEvent:
        processed = False
    async def mock_get(*args): return MockEvent()
    async def mock_process(*args): raise MockError("Business failed")
    async def mock_mark(*args): pass

    consumer = MockConsumer(mock_insert, mock_get, mock_process, mock_mark, dlq_topic=None)
    
    with patch("app.kafka.consumer.AsyncSessionLocal", return_value=AsyncMockSession()), \
         patch.object(consumer, "_commit_message", new_callable=AsyncMock) as commit_spy:

        raw_json = base_envelope.model_dump_json().encode("utf-8")
        message = ConsumerRecord(topic="cip.test.events", partition=0, offset=17, timestamp=0, timestamp_type=0, key=b"", value=raw_json, checksum=0, serialized_key_size=0, serialized_value_size=0, headers=())
        
        with pytest.raises(MockError):
            await consumer._handle_message(message)

        mock_producer.assert_not_called()
        commit_spy.assert_not_called()
