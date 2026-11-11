"""Configuration models for deterministic synthetic simulation.

All distributions, persona weights, and campaign influence ratios are centralized
and parameterized to avoid hardcoded constants or treated as immutable business truths.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class PersonaWeights:
    """Relative weights for assigning shopper personas."""

    browser: float = 0.50
    cart_abandoner: float = 0.25
    single_buyer: float = 0.20
    repeat_buyer: float = 0.05


@dataclass
class CampaignInfluenceWeights:
    """Probabilities and distribution parameters for campaign engagement and attribution."""

    delivery_rate: float = 0.85
    open_rate: float = 0.50
    click_rate: float = 0.30
    conversion_rate: float = 0.25
    direct_session_ratio: float = 0.60


@dataclass
class HistoricalSimulationConfig:
    """Configuration for historical multi-period simulation."""

    start_datetime: datetime
    end_datetime: datetime
    seed: int = 42
    merchant_count: int = 5
    products_per_merchant: int = 8
    variants_per_product: int = 3
    shoppers_per_merchant: int = 50
    campaigns_per_merchant: int = 3
    personas: PersonaWeights = field(default_factory=PersonaWeights)
    campaign_influence: CampaignInfluenceWeights = field(default_factory=CampaignInfluenceWeights)

    def __post_init__(self) -> None:
        if self.start_datetime.tzinfo is None:
            self.start_datetime = self.start_datetime.replace(tzinfo=timezone.utc)
        else:
            self.start_datetime = self.start_datetime.astimezone(timezone.utc)

        if self.end_datetime.tzinfo is None:
            self.end_datetime = self.end_datetime.replace(tzinfo=timezone.utc)
        else:
            self.end_datetime = self.end_datetime.astimezone(timezone.utc)

        if self.start_datetime >= self.end_datetime:
            raise ValueError(f"start_datetime ({self.start_datetime}) must be before end_datetime ({self.end_datetime})")

