import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, false, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MerchantEvent(Base):
    __tablename__ = "merchant_events"
    __table_args__ = (Index("ix_merchant_events_merchant_id_event_timestamp", "merchant_id", "event_timestamp"),)

    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchants.merchant_id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    event_version: Mapped[int] = mapped_column(Integer, nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false(), index=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    merchant: Mapped["Merchant"] = relationship()


class ShopperEvent(Base):
    __tablename__ = "shopper_events"
    __table_args__ = (
        Index("ix_shopper_events_merchant_id_event_timestamp", "merchant_id", "event_timestamp"),
        Index("ix_shopper_events_shopper_id_event_timestamp", "shopper_id", "event_timestamp"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchants.merchant_id"), nullable=False
    )
    shopper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shoppers.shopper_id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    event_version: Mapped[int] = mapped_column(Integer, nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false(), index=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    merchant: Mapped["Merchant"] = relationship()
    shopper: Mapped["Shopper"] = relationship()


class CampaignEvent(Base):
    __tablename__ = "campaign_events"
    __table_args__ = (
        Index("ix_campaign_events_campaign_id_event_timestamp", "campaign_id", "event_timestamp"),
        Index("ix_campaign_events_shopper_id_event_timestamp", "shopper_id", "event_timestamp"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.campaign_id"), nullable=False
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchants.merchant_id"), nullable=False
    )
    shopper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shoppers.shopper_id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    event_version: Mapped[int] = mapped_column(Integer, nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false(), index=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    campaign: Mapped["Campaign"] = relationship()
    merchant: Mapped["Merchant"] = relationship()
    shopper: Mapped["Shopper"] = relationship()


class PlatformEvent(Base):
    __tablename__ = "platform_events"

    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    event_version: Mapped[int] = mapped_column(Integer, nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
