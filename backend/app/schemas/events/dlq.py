from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DeadLetterRecord(BaseModel):
    """Structured record for a Dead Letter Queue (DLQ) entry."""

    model_config = ConfigDict(from_attributes=True)

    original_topic: str
    original_partition: int
    original_offset: int
    consumer_group_id: str
    failure_stage: Literal["validation", "processing"]
    error_type: str
    error_message: str
    failed_at: datetime
    original_message_base64: str

    # Optional diagnostic metadata
    original_event_id: UUID | None = None
    event_type: str | None = None

