from enum import Enum

from pydantic import BaseModel


class PlanKey(str, Enum):
    """Stable, machine-readable subscription plan identifier.

    Producer event contracts reference plans by this key rather than by a
    database plan_id, so events stay resolvable once reference-data
    initialization creates the matching subscription_plans rows.
    """

    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    PREMIUM = "premium"
    GROWTH = "growth"
    ENTERPRISE = "enterprise"


class BillingCycle(str, Enum):
    MONTHLY = "monthly"
    ANNUAL = "annual"


from app.reference_data.features import FeatureKey

class PlanCatalogEntry(BaseModel):
    plan_key: PlanKey
    plan_name: str
    monthly_price: float
    annual_price: float
    features: list[FeatureKey] = []


PLAN_CATALOG: dict[PlanKey, PlanCatalogEntry] = {
    PlanKey.FREE: PlanCatalogEntry(
        plan_key=PlanKey.FREE, plan_name="Free", monthly_price=0, annual_price=0,
        features=[FeatureKey.WISHLIST]
    ),
    PlanKey.STARTER: PlanCatalogEntry(
        plan_key=PlanKey.STARTER, plan_name="Starter", monthly_price=19, annual_price=190,
        features=[FeatureKey.WISHLIST, FeatureKey.SAVE_FOR_LATER, FeatureKey.BACK_IN_STOCK]
    ),
    PlanKey.PRO: PlanCatalogEntry(
        plan_key=PlanKey.PRO, plan_name="Pro", monthly_price=49, annual_price=490,
        features=[FeatureKey.WISHLIST, FeatureKey.SAVE_FOR_LATER, FeatureKey.BACK_IN_STOCK,
                  FeatureKey.RECOMMENDATIONS, FeatureKey.NUDGES, FeatureKey.MULTIPLE_WISHLISTS]
    ),
    PlanKey.PREMIUM: PlanCatalogEntry(
        plan_key=PlanKey.PREMIUM, plan_name="Premium", monthly_price=99, annual_price=990,
        features=[FeatureKey.WISHLIST, FeatureKey.SAVE_FOR_LATER, FeatureKey.BACK_IN_STOCK,
                  FeatureKey.RECOMMENDATIONS, FeatureKey.NUDGES, FeatureKey.MULTIPLE_WISHLISTS,
                  FeatureKey.KLAVIYO, FeatureKey.MAILCHIMP]
    ),
    PlanKey.GROWTH: PlanCatalogEntry(
        plan_key=PlanKey.GROWTH, plan_name="Growth", monthly_price=199, annual_price=1990,
        features=[FeatureKey.WISHLIST, FeatureKey.SAVE_FOR_LATER, FeatureKey.BACK_IN_STOCK,
                  FeatureKey.RECOMMENDATIONS, FeatureKey.NUDGES, FeatureKey.MULTIPLE_WISHLISTS,
                  FeatureKey.KLAVIYO, FeatureKey.MAILCHIMP, FeatureKey.OMNISEND,
                  FeatureKey.TWILIO, FeatureKey.META_PIXEL]
    ),
    PlanKey.ENTERPRISE: PlanCatalogEntry(
        plan_key=PlanKey.ENTERPRISE, plan_name="Enterprise", monthly_price=499, annual_price=4990,
        features=list(FeatureKey)
    ),
}
