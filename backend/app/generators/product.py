"""Deterministic, in-memory Product catalog lifecycle simulator.

Holds no database, Kafka, service, DAL, async, or cadence dependencies.
Builds validated ProductEventEnvelope objects for a caller to publish.

Usage:
    context = MerchantContext(merchant_id=uuid4(), merchant_name="Acme")
    generator = ProductCatalogGenerator(
        merchant_contexts=[context],
        products_per_merchant=5,
        variants_per_product=3,
        seed=42,
    )
    initial = generator.generate_catalog()   # PRODUCT_CREATED + VARIANT_CREATED per product
    later   = generator.tick()               # lifecycle events driven by RNG
"""

import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import NamedTuple

from app.schemas.events.envelope import ProductEventEnvelope
from app.schemas.events.event_types import ProductEventType
from app.schemas.events.payloads.product import (
    ProductArchivedPayload,
    ProductCreatedPayload,
    ProductUpdatedPayload,
    ProductVariantArchivedPayload,
    ProductVariantCreatedPayload,
    ProductVariantUpdatedPayload,
)

# ---------------------------------------------------------------------------
# Vocabulary tables
# ---------------------------------------------------------------------------

_CATEGORIES = (
    "Apparel",
    "Electronics",
    "Home & Garden",
    "Beauty",
    "Sports",
    "Toys",
    "Books",
    "Food & Beverage",
)
_VENDORS = ("BrandCo", "SupplyHouse", "MegaMfg", "LocalMaker", "GlobalSource")
_SIZES = ("XS", "S", "M", "L", "XL", "XXL", "One Size")
_COLORS = ("Red", "Blue", "Green", "Black", "White", "Grey", "Yellow", "Purple")
_STATUSES = ("active", "draft")

_ACTION_TICK_PROBABILITY = 0.55
# Per-product actions; add_product is handled at the merchant level during tick.
# Weights: update_product, update_variant, archive_variant, archive_product, add_variant
_PRODUCT_ACTIONS = (
    "update_product",
    "update_variant",
    "archive_variant",
    "archive_product",
    "add_variant",
)
_PRODUCT_ACTION_WEIGHTS = (4, 5, 2, 1, 3)

# Probability that a merchant-level new-product event is emitted during a tick
_NEW_PRODUCT_PROBABILITY = 0.15

_UPDATABLE_PRODUCT_FIELDS = ("product_name", "category", "vendor", "status")
# status is omitted: the only terminal transition for a variant is PRODUCT_VARIANT_ARCHIVED.
_UPDATABLE_VARIANT_FIELDS = ("variant_name", "price", "inventory_quantity", "size", "color")


# ---------------------------------------------------------------------------
# State dataclasses
# ---------------------------------------------------------------------------


class _VariantStage(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class _ProductStage(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


@dataclass
class _VariantState:
    variant_id: uuid.UUID
    variant_name: str
    sku: str
    price: Decimal
    size: str | None
    color: str | None
    inventory_quantity: int
    status: str
    stage: _VariantStage = _VariantStage.ACTIVE


@dataclass
class _ProductState:
    product_id: uuid.UUID
    merchant_id: uuid.UUID
    product_name: str
    category: str | None
    vendor: str | None
    status: str
    stage: _ProductStage = _ProductStage.ACTIVE
    variants: list[_VariantState] = field(default_factory=list)


class MerchantContext(NamedTuple):
    """Lightweight carrier of merchant identity for injection into the generator."""

    merchant_id: uuid.UUID
    merchant_name: str


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------


class ProductCatalogGenerator:
    """Deterministic, in-memory product catalog lifecycle simulator.

    Merchants are injected rather than loaded; the generator is pure and holds
    no I/O dependencies. A fresh instance always starts a brand-new synthetic
    catalog; the same configuration + seed always produces the same sequence of
    event types and field values.
    """

    def __init__(
        self,
        merchant_contexts: list[MerchantContext],
        products_per_merchant: int = 5,
        variants_per_product: int = 3,
        seed: int | None = None,
    ) -> None:
        if not merchant_contexts:
            raise ValueError("merchant_contexts must not be empty")
        self._rng = random.Random(seed)
        self._merchant_contexts = merchant_contexts
        self._products_per_merchant = products_per_merchant
        self._variants_per_product = variants_per_product
        self._products: list[_ProductState] = []
        self._product_counter: int = 0  # monotonic counter for stable synthetic names

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_catalog(self) -> list[ProductEventEnvelope]:
        """Emit PRODUCT_CREATED + PRODUCT_VARIANT_CREATED events for the initial catalog."""
        envelopes: list[ProductEventEnvelope] = []
        for ctx in self._merchant_contexts:
            for _ in range(self._products_per_merchant):
                product, product_envs = self._create_product(ctx.merchant_id)
                self._products.append(product)
                envelopes.extend(product_envs)
                for _ in range(self._variants_per_product):
                    variant, variant_env = self._create_variant(product)
                    product.variants.append(variant)
                    envelopes.append(variant_env)
        return envelopes

    def tick(self) -> list[ProductEventEnvelope]:
        """Advance the catalog one simulation step.

        Each active product gets an independent draw for a product-level action.
        Additionally, each distinct merchant with at least one active product gets
        an independent bounded chance to add a brand-new product.
        """
        envelopes: list[ProductEventEnvelope] = []

        # Per-product actions
        active_products = [p for p in self._products if p.stage == _ProductStage.ACTIVE]
        for product in active_products:
            if self._rng.random() > _ACTION_TICK_PROBABILITY:
                continue
            action = self._rng.choices(population=_PRODUCT_ACTIONS, weights=_PRODUCT_ACTION_WEIGHTS, k=1)[0]
            envelopes.extend(self._perform_action(product, action))

        # Per-merchant new-product opportunity (independent of per-product actions)
        active_merchant_ids = {p.merchant_id for p in self._products if p.stage == _ProductStage.ACTIVE}
        for merchant_id in sorted(active_merchant_ids):  # sorted for determinism
            if self._rng.random() < _NEW_PRODUCT_PROBABILITY:
                envelopes.extend(self._add_product_for_merchant(merchant_id))

        return envelopes

    def all_terminal(self) -> bool:
        """True when every product has been archived."""
        return all(p.stage == _ProductStage.ARCHIVED for p in self._products)

    # ------------------------------------------------------------------
    # Internal action dispatch
    # ------------------------------------------------------------------

    def _perform_action(self, product: _ProductState, action: str) -> list[ProductEventEnvelope]:
        if product.stage == _ProductStage.ARCHIVED:
            return []

        if action == "update_product":
            return self._update_product(product)

        if action == "update_variant":
            return self._update_variant(product)

        if action == "archive_variant":
            return self._archive_variant(product)

        if action == "archive_product":
            return self._archive_product(product)

        if action == "add_variant":
            return self._add_variant_to_existing(product)

        return []

    def _update_product(self, product: _ProductState) -> list[ProductEventEnvelope]:
        field_name = self._rng.choice(_UPDATABLE_PRODUCT_FIELDS)
        new_value: str | None
        if field_name == "product_name":
            new_value = self._product_name(self._product_counter)
            self._product_counter += 1
        elif field_name == "category":
            new_value = self._rng.choice(_CATEGORIES)
            product.category = new_value
        elif field_name == "vendor":
            new_value = self._rng.choice(_VENDORS)
            product.vendor = new_value
        else:  # status
            new_value = self._rng.choice(_STATUSES)
            product.status = new_value
        if field_name == "product_name":
            product.product_name = new_value  # type: ignore[assignment]
        return [
            self._build_envelope(
                product,
                ProductEventType.PRODUCT_UPDATED,
                ProductUpdatedPayload(changed_values={field_name: new_value}),
            )
        ]

    def _update_variant(self, product: _ProductState) -> list[ProductEventEnvelope]:
        active = [v for v in product.variants if v.stage == _VariantStage.ACTIVE]
        if not active:
            return []
        variant = self._rng.choice(active)
        field_name = self._rng.choice(_UPDATABLE_VARIANT_FIELDS)
        new_value: object
        if field_name == "variant_name":
            new_value = f"Variant-{variant.variant_id.hex[:6]}-upd"
            variant.variant_name = str(new_value)
        elif field_name == "price":
            new_value = self._random_price()
            variant.price = new_value  # type: ignore[assignment]
        elif field_name == "inventory_quantity":
            new_value = self._rng.randint(0, 500)
            variant.inventory_quantity = int(new_value)
        elif field_name == "size":
            new_value = self._rng.choice(_SIZES)
            variant.size = str(new_value)
        else:  # color
            new_value = self._rng.choice(_COLORS)
            variant.color = str(new_value)
        # Decimal must be serialisable in changed_values; convert to str for JSON safety
        serialised = str(new_value) if isinstance(new_value, Decimal) else new_value
        return [
            self._build_envelope(
                product,
                ProductEventType.PRODUCT_VARIANT_UPDATED,
                ProductVariantUpdatedPayload(
                    variant_id=variant.variant_id,
                    changed_values={field_name: serialised},
                ),
            )
        ]

    def _archive_variant(self, product: _ProductState) -> list[ProductEventEnvelope]:
        active = [v for v in product.variants if v.stage == _VariantStage.ACTIVE]
        if not active:
            return []
        variant = self._rng.choice(active)
        variant.stage = _VariantStage.ARCHIVED
        return [
            self._build_envelope(
                product,
                ProductEventType.PRODUCT_VARIANT_ARCHIVED,
                ProductVariantArchivedPayload(variant_id=variant.variant_id),
            )
        ]

    def _archive_product(self, product: _ProductState) -> list[ProductEventEnvelope]:
        # Silently mark all active variants as archived in internal state so that
        # invariants hold (no post-archive updates/creates). PRODUCT_VARIANT_ARCHIVED
        # events are NOT emitted here; dependent operational archival is handled by
        # Unit 3.5D business processing when it consumes PRODUCT_ARCHIVED.
        for variant in product.variants:
            if variant.stage == _VariantStage.ACTIVE:
                variant.stage = _VariantStage.ARCHIVED
        product.stage = _ProductStage.ARCHIVED
        return [
            self._build_envelope(
                product,
                ProductEventType.PRODUCT_ARCHIVED,
                ProductArchivedPayload(),
            )
        ]

    def _add_product_for_merchant(self, merchant_id: uuid.UUID) -> list[ProductEventEnvelope]:
        product, envs = self._create_product(merchant_id)
        self._products.append(product)
        variant, variant_env = self._create_variant(product)
        product.variants.append(variant)
        envs.append(variant_env)
        return envs

    def _add_variant_to_existing(self, product: _ProductState) -> list[ProductEventEnvelope]:
        if product.stage == _ProductStage.ARCHIVED:
            return []
        variant, env = self._create_variant(product)
        product.variants.append(variant)
        return [env]

    # ------------------------------------------------------------------
    # Creation helpers
    # ------------------------------------------------------------------

    def _create_product(self, merchant_id: uuid.UUID) -> tuple[_ProductState, list[ProductEventEnvelope]]:
        product_id = uuid.uuid4()
        self._product_counter += 1
        name = self._product_name(self._product_counter)
        category = self._rng.choice(_CATEGORIES)
        vendor = self._rng.choice(_VENDORS)
        status = self._rng.choice(_STATUSES)
        product = _ProductState(
            product_id=product_id,
            merchant_id=merchant_id,
            product_name=name,
            category=category,
            vendor=vendor,
            status=status,
        )
        envelope = self._build_envelope(
            product,
            ProductEventType.PRODUCT_CREATED,
            ProductCreatedPayload(
                product_name=name,
                category=category,
                vendor=vendor,
                status=status,
            ),
        )
        return product, [envelope]

    def _create_variant(self, product: _ProductState) -> tuple[_VariantState, ProductEventEnvelope]:
        variant_id = uuid.uuid4()
        sku = f"SKU-{product.product_id.hex[:6]}-{variant_id.hex[:6]}"
        variant_name = f"Variant-{variant_id.hex[:6]}"
        price = self._random_price()
        size = self._rng.choice(_SIZES) if self._rng.random() < 0.7 else None
        color = self._rng.choice(_COLORS) if self._rng.random() < 0.7 else None
        inventory_quantity = self._rng.randint(0, 300)
        status = "active"
        variant = _VariantState(
            variant_id=variant_id,
            variant_name=variant_name,
            sku=sku,
            price=price,
            size=size,
            color=color,
            inventory_quantity=inventory_quantity,
            status=status,
        )
        envelope = self._build_envelope(
            product,
            ProductEventType.PRODUCT_VARIANT_CREATED,
            ProductVariantCreatedPayload(
                variant_id=variant_id,
                variant_name=variant_name,
                sku=sku,
                price=price,
                size=size,
                color=color,
                inventory_quantity=inventory_quantity,
                status=status,
            ),
        )
        return variant, envelope

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _random_price(self) -> Decimal:
        """Return a non-negative price with 2 decimal places as Decimal."""
        cents = self._rng.randint(99, 99999)  # $0.99 – $999.99
        return Decimal(cents) / Decimal("100")

    @staticmethod
    def _product_name(counter: int) -> str:
        return f"Product-{counter:06d}"

    def _build_envelope(
        self,
        product: _ProductState,
        event_type: ProductEventType,
        payload: object,
    ) -> ProductEventEnvelope:
        return ProductEventEnvelope(
            event_id=uuid.uuid4(),
            event_type=event_type,
            event_version=1,
            event_timestamp=datetime.now(timezone.utc),
            merchant_id=product.merchant_id,
            product_id=product.product_id,
            payload=payload.model_dump(mode="json"),  # type: ignore[attr-defined]
            source="product-generator",
        )

