from enum import Enum

from pydantic import BaseModel


class FeatureKey(str, Enum):
    """Stable, machine-readable platform feature identifier.

    Producer event contracts reference features by this key rather than by a
    database feature_id, so events stay resolvable once reference-data
    initialization creates the matching platform_features rows.
    """

    WISHLIST = "wishlist"
    SAVE_FOR_LATER = "save_for_later"
    BACK_IN_STOCK = "back_in_stock"
    RECOMMENDATIONS = "recommendations"
    NUDGES = "nudges"
    MULTIPLE_WISHLISTS = "multiple_wishlists"
    KLAVIYO = "klaviyo"
    MAILCHIMP = "mailchimp"
    OMNISEND = "omnisend"
    TWILIO = "twilio"
    META_PIXEL = "meta_pixel"


class FeatureEventMappingEntry(BaseModel):
    event_domain: str
    event_type: str


class FeatureCatalogEntry(BaseModel):
    feature_key: FeatureKey
    feature_name: str
    feature_category: str
    event_mappings: list[FeatureEventMappingEntry] = []


FEATURE_CATALOG: dict[FeatureKey, FeatureCatalogEntry] = {
    FeatureKey.WISHLIST: FeatureCatalogEntry(
        feature_key=FeatureKey.WISHLIST, feature_name="Wishlist", feature_category="shopper_engagement",
        event_mappings=[
            FeatureEventMappingEntry(event_domain="shopper", event_type="WISHLIST_ADDED"),
            FeatureEventMappingEntry(event_domain="shopper", event_type="WISHLIST_REMOVED"),
        ]
    ),
    FeatureKey.SAVE_FOR_LATER: FeatureCatalogEntry(
        feature_key=FeatureKey.SAVE_FOR_LATER,
        feature_name="Save for Later",
        feature_category="shopper_engagement",
        event_mappings=[
            FeatureEventMappingEntry(event_domain="shopper", event_type="SAVE_FOR_LATER_ADDED"),
            FeatureEventMappingEntry(event_domain="shopper", event_type="SAVE_FOR_LATER_REMOVED"),
        ]
    ),
    FeatureKey.BACK_IN_STOCK: FeatureCatalogEntry(
        feature_key=FeatureKey.BACK_IN_STOCK,
        feature_name="Back in Stock Alerts",
        feature_category="shopper_engagement",
    ),
    FeatureKey.RECOMMENDATIONS: FeatureCatalogEntry(
        feature_key=FeatureKey.RECOMMENDATIONS,
        feature_name="Recommendations",
        feature_category="shopper_engagement",
        event_mappings=[
            FeatureEventMappingEntry(event_domain="shopper", event_type="RECOMMENDATION_VIEWED"),
            FeatureEventMappingEntry(event_domain="shopper", event_type="RECOMMENDATION_CLICKED"),
        ]
    ),
    FeatureKey.NUDGES: FeatureCatalogEntry(
        feature_key=FeatureKey.NUDGES, feature_name="Nudges", feature_category="shopper_engagement"
    ),
    FeatureKey.MULTIPLE_WISHLISTS: FeatureCatalogEntry(
        feature_key=FeatureKey.MULTIPLE_WISHLISTS,
        feature_name="Multiple Wishlists",
        feature_category="shopper_engagement",
    ),
    FeatureKey.KLAVIYO: FeatureCatalogEntry(
        feature_key=FeatureKey.KLAVIYO, feature_name="Klaviyo Integration", feature_category="marketing_integration"
    ),
    FeatureKey.MAILCHIMP: FeatureCatalogEntry(
        feature_key=FeatureKey.MAILCHIMP,
        feature_name="Mailchimp Integration",
        feature_category="marketing_integration",
    ),
    FeatureKey.OMNISEND: FeatureCatalogEntry(
        feature_key=FeatureKey.OMNISEND,
        feature_name="Omnisend Integration",
        feature_category="marketing_integration",
    ),
    FeatureKey.TWILIO: FeatureCatalogEntry(
        feature_key=FeatureKey.TWILIO,
        feature_name="Twilio SMS Integration",
        feature_category="marketing_integration",
    ),
    FeatureKey.META_PIXEL: FeatureCatalogEntry(
        feature_key=FeatureKey.META_PIXEL,
        feature_name="Meta Pixel Integration",
        feature_category="advertising_integration",
    ),
}
