from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MerchantProfile(Base):
    __tablename__ = "merchant_profiles"

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchants.merchant_id"), primary_key=True
    )
    total_shoppers: Mapped[int] = mapped_column(Integer, nullable=False)
    total_products: Mapped[int] = mapped_column(Integer, nullable=False)
    total_orders: Mapped[int] = mapped_column(Integer, nullable=False)
    total_revenue: Mapped[float] = mapped_column(Numeric, nullable=False)
    average_order_value: Mapped[float] = mapped_column(Numeric, nullable=False)
    conversion_rate: Mapped[float] = mapped_column(Numeric, nullable=False)
    total_campaigns: Mapped[int] = mapped_column(Integer, nullable=False)
    active_campaign_count: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled_feature_count: Mapped[int] = mapped_column(Integer, nullable=False)
    last_order_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_campaign_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    merchant: Mapped["Merchant"] = relationship()


class ShopperProfile(Base):
    __tablename__ = "shopper_profiles"

    shopper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shoppers.shopper_id"), primary_key=True
    )
    total_orders: Mapped[int] = mapped_column(Integer, nullable=False)
    total_spend: Mapped[float] = mapped_column(Numeric, nullable=False)
    average_order_value: Mapped[float] = mapped_column(Numeric, nullable=False)
    customer_lifetime_value: Mapped[float] = mapped_column(Numeric, nullable=False)
    purchase_frequency: Mapped[float] = mapped_column(Numeric, nullable=False)
    wishlist_item_count: Mapped[int] = mapped_column(Integer, nullable=False)
    save_for_later_item_count: Mapped[int] = mapped_column(Integer, nullable=False)
    cart_abandonment_count: Mapped[int] = mapped_column(Integer, nullable=False)
    campaign_engagement_count: Mapped[int] = mapped_column(Integer, nullable=False)
    preferred_category: Mapped[str | None] = mapped_column(String)
    preferred_size: Mapped[str | None] = mapped_column(String)
    last_purchase_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lifecycle_stage: Mapped[str | None] = mapped_column(String)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    shopper: Mapped["Shopper"] = relationship()
