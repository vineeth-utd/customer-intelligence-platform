from datetime import date, datetime
import uuid

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CampaignAnalyticsDaily(Base):
    __tablename__ = "campaign_analytics_daily"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.campaign_id"), primary_key=True
    )
    metric_date: Mapped[date] = mapped_column(Date, primary_key=True)
    delivered_count: Mapped[int] = mapped_column(Integer, nullable=False)
    opened_count: Mapped[int] = mapped_column(Integer, nullable=False)
    clicked_count: Mapped[int] = mapped_column(Integer, nullable=False)
    converted_count: Mapped[int] = mapped_column(Integer, nullable=False)
    attributed_order_count: Mapped[int] = mapped_column(Integer, nullable=False)
    attributed_revenue: Mapped[float] = mapped_column(Numeric, nullable=False)
    open_rate: Mapped[float] = mapped_column(Numeric, nullable=False)
    click_through_rate: Mapped[float] = mapped_column(Numeric, nullable=False)
    conversion_rate: Mapped[float] = mapped_column(Numeric, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    campaign: Mapped["Campaign"] = relationship()


class MerchantMetricsDaily(Base):
    __tablename__ = "merchant_metrics_daily"

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchants.merchant_id"), primary_key=True
    )
    metric_date: Mapped[date] = mapped_column(Date, primary_key=True)
    revenue: Mapped[float] = mapped_column(Numeric, nullable=False)
    order_count: Mapped[int] = mapped_column(Integer, nullable=False)
    unique_shoppers: Mapped[int] = mapped_column(Integer, nullable=False)
    new_shoppers: Mapped[int] = mapped_column(Integer, nullable=False)
    session_count: Mapped[int] = mapped_column(Integer, nullable=False)
    converted_session_count: Mapped[int] = mapped_column(Integer, nullable=False)
    product_view_count: Mapped[int] = mapped_column(Integer, nullable=False)
    wishlist_add_count: Mapped[int] = mapped_column(Integer, nullable=False)
    save_for_later_count: Mapped[int] = mapped_column(Integer, nullable=False)
    add_to_cart_count: Mapped[int] = mapped_column(Integer, nullable=False)
    checkout_count: Mapped[int] = mapped_column(Integer, nullable=False)
    purchase_count: Mapped[int] = mapped_column(Integer, nullable=False)
    conversion_rate: Mapped[float] = mapped_column(Numeric, nullable=False)
    average_order_value: Mapped[float] = mapped_column(Numeric, nullable=False)
    platform_login_count: Mapped[int] = mapped_column(Integer, nullable=False)
    campaign_created_count: Mapped[int] = mapped_column(Integer, nullable=False)
    feature_enable_count: Mapped[int] = mapped_column(Integer, nullable=False)
    feature_disable_count: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    merchant: Mapped["Merchant"] = relationship()


class PlatformMetricsDaily(Base):
    __tablename__ = "platform_metrics_daily"

    metric_date: Mapped[date] = mapped_column(Date, primary_key=True)
    active_merchants: Mapped[int] = mapped_column(Integer, nullable=False)
    new_merchants: Mapped[int] = mapped_column(Integer, nullable=False)
    installed_merchants: Mapped[int] = mapped_column(Integer, nullable=False)
    uninstalled_merchants: Mapped[int] = mapped_column(Integer, nullable=False)
    new_subscriptions: Mapped[int] = mapped_column(Integer, nullable=False)
    subscription_upgrades: Mapped[int] = mapped_column(Integer, nullable=False)
    subscription_downgrades: Mapped[int] = mapped_column(Integer, nullable=False)
    subscription_cancellations: Mapped[int] = mapped_column(Integer, nullable=False)
    total_revenue: Mapped[float] = mapped_column(Numeric, nullable=False)
    total_orders: Mapped[int] = mapped_column(Integer, nullable=False)
    active_shoppers: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FeatureMetricsDaily(Base):
    __tablename__ = "feature_metrics_daily"

    feature_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_features.feature_id"), primary_key=True
    )
    metric_date: Mapped[date] = mapped_column(Date, primary_key=True)
    eligible_merchant_count: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled_merchant_count: Mapped[int] = mapped_column(Integer, nullable=False)
    active_merchant_count: Mapped[int] = mapped_column(Integer, nullable=False)
    feature_event_count: Mapped[int] = mapped_column(Integer, nullable=False)
    adoption_rate: Mapped[float] = mapped_column(Numeric, nullable=False)
    usage_rate: Mapped[float] = mapped_column(Numeric, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    feature: Mapped["PlatformFeature"] = relationship()
