import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EntityProcessingState(Base):
    __tablename__ = "entity_processing_states"

    entity_type: Mapped[str] = mapped_column(String, primary_key=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    target_type: Mapped[str] = mapped_column(String, primary_key=True)
    last_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_generation_status: Mapped[str] = mapped_column(String, nullable=False, server_default="PENDING")
    last_error: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
