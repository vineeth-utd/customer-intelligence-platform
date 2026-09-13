from datetime import datetime
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CustomerJourney(Base):
    __tablename__ = "customer_journeys"

    journey_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchants.merchant_id"), nullable=False
    )
    shopper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shoppers.shopper_id"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    journey_status: Mapped[str] = mapped_column(String, nullable=False)
    converted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.order_id"))
    entry_source: Mapped[str | None] = mapped_column(String)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    merchant: Mapped["Merchant"] = relationship()
    shopper: Mapped["Shopper"] = relationship()
    order: Mapped["Order | None"] = relationship()
    events: Mapped[list["CustomerJourneyEvent"]] = relationship(back_populates="journey")


class CustomerJourneyEvent(Base):
    __tablename__ = "customer_journey_events"

    journey_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    journey_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customer_journeys.journey_id"), nullable=False
    )
    source_event_category: Mapped[str] = mapped_column(String, nullable=False)
    source_event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)

    journey: Mapped["CustomerJourney"] = relationship(back_populates="events")


class MerchantJourney(Base):
    __tablename__ = "merchant_journeys"

    merchant_journey_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchants.merchant_id"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    journey_status: Mapped[str] = mapped_column(String, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    merchant: Mapped["Merchant"] = relationship()
    events: Mapped[list["MerchantJourneyEvent"]] = relationship(back_populates="merchant_journey")


class MerchantJourneyEvent(Base):
    __tablename__ = "merchant_journey_events"

    merchant_journey_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    merchant_journey_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchant_journeys.merchant_journey_id"), nullable=False
    )
    source_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchant_events.event_id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)

    merchant_journey: Mapped["MerchantJourney"] = relationship(back_populates="events")
    source_event: Mapped["MerchantEvent"] = relationship()
