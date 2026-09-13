from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ShopperSegmentMember(Base):
    __tablename__ = "shopper_segment_members"

    segment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shopper_segments.segment_id"), primary_key=True
    )
    shopper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shoppers.shopper_id"), primary_key=True
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    segment: Mapped["ShopperSegment"] = relationship()
    shopper: Mapped["Shopper"] = relationship()
