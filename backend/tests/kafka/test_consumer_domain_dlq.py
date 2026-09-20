from app.kafka.consumer import (
    MerchantEventConsumer,
    ProductEventConsumer,
    ShopperEventConsumer,
    CampaignEventConsumer,
)
from app.config.settings import settings
from app.services import merchant, product, shopper, campaign

def test_domain_consumer_dlq_configuration():
    mc = MerchantEventConsumer()
    assert mc._dlq_topic == settings.kafka_merchant_dlq_topic
    assert merchant.UnresolvedReferenceError in mc._business_exceptions
    assert merchant.UnsupportedConfigurationFieldError in mc._business_exceptions

    pc = ProductEventConsumer()
    assert pc._dlq_topic == settings.kafka_product_dlq_topic
    assert product.UnresolvedReferenceError in pc._business_exceptions
    assert product.UnsupportedProductFieldError in pc._business_exceptions
    assert product.UnsupportedVariantFieldError in pc._business_exceptions
    assert product.InvalidChangedValueError in pc._business_exceptions

    sc = ShopperEventConsumer()
    assert sc._dlq_topic == settings.kafka_shopper_dlq_topic
    assert shopper.IdentityConflictError in sc._business_exceptions
    assert shopper.UnresolvedReferenceError in sc._business_exceptions
    assert shopper.InsufficientInventoryError in sc._business_exceptions

    cc = CampaignEventConsumer()
    assert cc._dlq_topic == settings.kafka_campaign_dlq_topic
    assert campaign.UnresolvedReferenceError in cc._business_exceptions
    assert campaign.UnsupportedConfigurationFieldError in cc._business_exceptions
    assert campaign.AttributionError in cc._business_exceptions
