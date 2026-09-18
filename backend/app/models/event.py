import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, false, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MerchantEvent(Base):
    """Merchant entity identifiers on event tables are required lineage/
    correlation identifiers, not enforced foreign keys - see docs/11_Database
    _Design.md 4.2. Event persistence must succeed independently of whether
    the referenced operational entity (e.g. Merchant) has been created yet.
    """

    __tablename__ = "merchant_events"
    __table_args__ = (Index("ix_merchant_events_merchant_id_event_timestamp", "merchant_id", "event_timestamp"),)

    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    merchant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    event_version: Mapped[int] = mapped_column(Integer, nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false(), index=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ShopperEvent(Base):
    __tablename__ = "shopper_events"
    __table_args__ = (
        Index("ix_shopper_events_merchant_id_event_timestamp", "merchant_id", "event_timestamp"),
        Index("ix_shopper_events_shopper_id_event_timestamp", "shopper_id", "event_timestamp"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    merchant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    shopper_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    event_version: Mapped[int] = mapped_column(Integer, nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false(), index=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CampaignEvent(Base):
    __tablename__ = "campaign_events"
    __table_args__ = (
        Index("ix_campaign_events_campaign_id_event_timestamp", "campaign_id", "event_timestamp"),
        Index("ix_campaign_events_shopper_id_event_timestamp", "shopper_id", "event_timestamp"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    merchant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    shopper_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    event_version: Mapped[int] = mapped_column(Integer, nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false(), index=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ProductEvent(Base):
    """Merchant/product entity identifiers on event tables are required lineage/
    correlation identifiers, not enforced foreign keys - see docs/11_Database
    _Design.md 4.2. Event persistence must succeed independently of whether
    the referenced operational entity (e.g. Product) has been created yet.
    """

    __tablename__ = "product_events"
    __table_args__ = (
        Index("ix_product_events_merchant_id_event_timestamp", "merchant_id", "event_timestamp"),
        Index("ix_product_events_product_id_event_timestamp", "product_id", "event_timestamp"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    merchant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    event_version: Mapped[int] = mapped_column(Integer, nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false(), index=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PlatformEvent(Base):
    __tablename__ = "platform_events"

    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    event_version: Mapped[int] = mapped_column(Integer, nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
