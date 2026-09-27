from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PlatformSummaryResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_merchants: int
    active_merchants: int
    total_revenue: Decimal
    total_orders: int
    active_shoppers: int
    active_subscriptions: int


class PlatformTrendResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    metric_date: date
    active_merchants: int
    new_merchants: int
    installed_merchants: int
    uninstalled_merchants: int
    new_subscriptions: int
    subscription_upgrades: int
    subscription_downgrades: int
    subscription_cancellations: int
    total_revenue: Decimal
    total_orders: int
    active_shoppers: int


class FeatureMetricsResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    feature_id: UUID
    feature_key: str
    feature_name: str
    feature_category: str
    eligible_merchant_count: int
    enabled_merchant_count: int
    active_merchant_count: int
    total_feature_events: int
    adoption_rate: Decimal
    usage_rate: Decimal


class MerchantMetricsSummaryResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    merchant_id: UUID
    revenue: Decimal
    order_count: int
    unique_shoppers: int
    new_shoppers: int
    session_count: int
    converted_session_count: int
    product_view_count: int
    wishlist_add_count: int
    save_for_later_count: int
    add_to_cart_count: int
    checkout_count: int
    purchase_count: int
    conversion_rate: Decimal
    average_order_value: Decimal
    platform_login_count: int
    campaign_created_count: int
    feature_enable_count: int
    feature_disable_count: int


class MerchantMetricsTrendResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    metric_date: date
    merchant_id: UUID
    revenue: Decimal
    order_count: int
    unique_shoppers: int
    new_shoppers: int
    session_count: int
    converted_session_count: int
    product_view_count: int
    wishlist_add_count: int
    save_for_later_count: int
    add_to_cart_count: int
    checkout_count: int
    purchase_count: int
    conversion_rate: Decimal
    average_order_value: Decimal
    platform_login_count: int
    campaign_created_count: int
    feature_enable_count: int
    feature_disable_count: int


class CampaignAnalyticsResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    campaign_id: UUID
    campaign_name: str
    campaign_type: str
    campaign_medium: str
    status: str
    delivered_count: int
    opened_count: int
    clicked_count: int
    converted_count: int
    attributed_order_count: int
    attributed_revenue: Decimal
    open_rate: Decimal
    click_through_rate: Decimal
    conversion_rate: Decimal
