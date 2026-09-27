"""Unit tests for ProductCatalogGenerator.

These tests are pure and require no external infrastructure (no Kafka, no
PostgreSQL). They cover: determinism, creation ordering, stable IDs, merchant
ownership, terminal-state invariants, non-negative inventory, and valid prices.
"""

import uuid
from decimal import Decimal

import pytest

from app.generators.product import (
    _PRODUCT_ACTIONS,
    _UPDATABLE_VARIANT_FIELDS,
    MerchantContext,
    ProductCatalogGenerator,
    _ProductStage,
    _VariantStage,
)
from app.schemas.events.envelope import ProductEventEnvelope
from app.schemas.events.event_types import ProductEventType


class _FakeAlwaysTriggerRng:
    """Deterministic stand-in for random.Random that always takes the
    "trigger" branch and always picks the first option, used to make tick()
    behaviour deterministic for bounded-opportunity assertions."""

    def random(self) -> float:
        return 0.0

    def choices(self, population, weights=None, k=1):
        return [population[0]] * k

    def choice(self, seq):
        return seq[0]

    def randint(self, a, b):
        return a


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _two_merchants() -> list[MerchantContext]:
    return [
        MerchantContext(merchant_id=uuid.uuid4(), merchant_name="Merchant A"),
        MerchantContext(merchant_id=uuid.uuid4(), merchant_name="Merchant B"),
    ]


def _make_generator(
    merchants: list[MerchantContext] | None = None,
    products_per_merchant: int = 3,
    variants_per_product: int = 2,
    seed: int = 42,
) -> ProductCatalogGenerator:
    return ProductCatalogGenerator(
        merchant_contexts=merchants or _two_merchants(),
        products_per_merchant=products_per_merchant,
        variants_per_product=variants_per_product,
        seed=seed,
    )


def _event_types(envelopes: list[ProductEventEnvelope]) -> list[str]:
    return [e.event_type.value for e in envelopes]


# ---------------------------------------------------------------------------
# Construction guards
# ---------------------------------------------------------------------------


def test_empty_merchant_contexts_raises():
    with pytest.raises(ValueError, match="merchant_contexts must not be empty"):
        ProductCatalogGenerator(merchant_contexts=[])


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_same_seed_produces_identical_event_type_sequence():
    merchants = _two_merchants()
    # Re-use the same merchant UUIDs for both instances so the catalog is structurally identical
    gen_a = ProductCatalogGenerator(merchant_contexts=merchants, products_per_merchant=4, variants_per_product=2, seed=7)
    gen_b = ProductCatalogGenerator(merchant_contexts=merchants, products_per_merchant=4, variants_per_product=2, seed=7)

    seq_a = _event_types(gen_a.generate_catalog())
    seq_b = _event_types(gen_b.generate_catalog())
    for _ in range(20):
        seq_a.extend(_event_types(gen_a.tick()))
        seq_b.extend(_event_types(gen_b.tick()))

    assert seq_a == seq_b


def test_different_seeds_can_produce_different_tick_sequences():
    merchants = _two_merchants()
    gen_a = ProductCatalogGenerator(merchant_contexts=merchants, products_per_merchant=4, variants_per_product=2, seed=7)
    gen_b = ProductCatalogGenerator(merchant_contexts=merchants, products_per_merchant=4, variants_per_product=2, seed=99)
    gen_a.generate_catalog()
    gen_b.generate_catalog()
    ticks_a = [_event_types(gen_a.tick()) for _ in range(30)]
    ticks_b = [_event_types(gen_b.tick()) for _ in range(30)]
    # At least one tick should differ for well-separated seeds
    assert ticks_a != ticks_b


# ---------------------------------------------------------------------------
# Initial creation ordering
# ---------------------------------------------------------------------------


def test_initial_catalog_interleaves_product_created_then_variants():
    ctx = MerchantContext(merchant_id=uuid.uuid4(), merchant_name="Solo")
    gen = ProductCatalogGenerator(
        merchant_contexts=[ctx],
        products_per_merchant=2,
        variants_per_product=3,
        seed=1,
    )
    envelopes = gen.generate_catalog()
    # Each product block: 1 PRODUCT_CREATED + N VARIANT_CREATED
    block_size = 1 + 3
    assert len(envelopes) == 2 * block_size
    for block_start in (0, block_size):
        assert envelopes[block_start].event_type == ProductEventType.PRODUCT_CREATED
        for offset in range(1, 4):
            assert envelopes[block_start + offset].event_type == ProductEventType.PRODUCT_VARIANT_CREATED


def test_variant_created_references_same_product_id_as_product_created():
    ctx = MerchantContext(merchant_id=uuid.uuid4(), merchant_name="Solo")
    gen = ProductCatalogGenerator(
        merchant_contexts=[ctx],
        products_per_merchant=1,
        variants_per_product=2,
        seed=1,
    )
    envelopes = gen.generate_catalog()
    product_id = envelopes[0].product_id
    for env in envelopes[1:]:
        assert env.product_id == product_id


# ---------------------------------------------------------------------------
# Merchant ownership
# ---------------------------------------------------------------------------


def test_all_envelopes_carry_their_merchant_id():
    merchants = _two_merchants()
    gen = _make_generator(merchants=merchants, products_per_merchant=2, variants_per_product=2)
    envelopes = gen.generate_catalog()
    merchant_ids = {m.merchant_id for m in merchants}
    for env in envelopes:
        assert env.merchant_id in merchant_ids


def test_products_are_segregated_by_merchant():
    merchants = [
        MerchantContext(merchant_id=uuid.uuid4(), merchant_name="A"),
        MerchantContext(merchant_id=uuid.uuid4(), merchant_name="B"),
    ]
    gen = ProductCatalogGenerator(
        merchant_contexts=merchants,
        products_per_merchant=3,
        variants_per_product=1,
        seed=5,
    )
    envelopes = gen.generate_catalog()
    product_created = [e for e in envelopes if e.event_type == ProductEventType.PRODUCT_CREATED]
    assert len(product_created) == 6  # 3 per merchant
    merchant_a_products = [e for e in product_created if e.merchant_id == merchants[0].merchant_id]
    merchant_b_products = [e for e in product_created if e.merchant_id == merchants[1].merchant_id]
    assert len(merchant_a_products) == 3
    assert len(merchant_b_products) == 3


# ---------------------------------------------------------------------------
# Stable IDs across updates
# ---------------------------------------------------------------------------


def test_product_id_is_stable_across_ticks():
    ctx = MerchantContext(merchant_id=uuid.uuid4(), merchant_name="StableID")
    gen = ProductCatalogGenerator(
        merchant_contexts=[ctx],
        products_per_merchant=2,
        variants_per_product=2,
        seed=10,
    )
    gen.generate_catalog()
    initial_ids = {p.product_id for p in gen._products}

    # Force update events for all products over many ticks
    for _ in range(50):
        gen.tick()

    current_ids = {p.product_id for p in gen._products}
    # Original products retain their IDs (new ones may have been added by add_product action)
    assert initial_ids.issubset(current_ids)


def test_variant_id_is_stable_across_updates():
    ctx = MerchantContext(merchant_id=uuid.uuid4(), merchant_name="VarStable")
    gen = ProductCatalogGenerator(
        merchant_contexts=[ctx],
        products_per_merchant=1,
        variants_per_product=3,
        seed=20,
    )
    gen.generate_catalog()
    initial_variant_ids = {v.variant_id for p in gen._products for v in p.variants}

    for _ in range(50):
        gen.tick()

    current_variant_ids = {v.variant_id for p in gen._products for v in p.variants}
    assert initial_variant_ids.issubset(current_variant_ids)


# ---------------------------------------------------------------------------
# Terminal-state invariants
# ---------------------------------------------------------------------------


def test_archived_product_emits_no_further_events():
    ctx = MerchantContext(merchant_id=uuid.uuid4(), merchant_name="Terminal")
    gen = ProductCatalogGenerator(
        merchant_contexts=[ctx],
        products_per_merchant=1,
        variants_per_product=2,
        seed=3,
    )
    gen.generate_catalog()

    # Directly archive the only product
    product = gen._products[0]
    gen._archive_product(product)
    assert product.stage == _ProductStage.ARCHIVED

    # tick must produce nothing for this product
    events_after = []
    for _ in range(20):
        events_after.extend(gen.tick())
    product_events = [e for e in events_after if e.product_id == product.product_id]
    assert product_events == []


def test_archived_variants_are_not_updated():
    ctx = MerchantContext(merchant_id=uuid.uuid4(), merchant_name="ArchiveVar")
    gen = ProductCatalogGenerator(
        merchant_contexts=[ctx],
        products_per_merchant=1,
        variants_per_product=3,
        seed=4,
    )
    gen.generate_catalog()
    product = gen._products[0]

    # Archive all variants directly
    for v in product.variants:
        v.stage = _VariantStage.ARCHIVED

    # _update_variant must return nothing when all variants are archived
    result = gen._update_variant(product)
    assert result == []


def test_product_archived_silently_archives_variants_and_emits_only_product_archived():
    ctx = MerchantContext(merchant_id=uuid.uuid4(), merchant_name="DepArchive")
    gen = ProductCatalogGenerator(
        merchant_contexts=[ctx],
        products_per_merchant=1,
        variants_per_product=4,
        seed=55,
    )
    gen.generate_catalog()
    product = gen._products[0]

    # Pre-archive one variant to test partial state
    product.variants[0].stage = _VariantStage.ARCHIVED

    envelopes = gen._archive_product(product)

    # Only PRODUCT_ARCHIVED is emitted — no PRODUCT_VARIANT_ARCHIVED events
    assert len(envelopes) == 1
    assert envelopes[0].event_type == ProductEventType.PRODUCT_ARCHIVED
    assert envelopes[0].product_id == product.product_id

    # All 4 variant states are silently archived in memory
    assert all(v.stage == _VariantStage.ARCHIVED for v in product.variants)
    assert product.stage == _ProductStage.ARCHIVED

    # No PRODUCT_VARIANT_ARCHIVED events are in the output
    variant_archived_events = [e for e in envelopes if e.event_type == ProductEventType.PRODUCT_VARIANT_ARCHIVED]
    assert variant_archived_events == []


def test_no_variants_created_under_archived_product():
    ctx = MerchantContext(merchant_id=uuid.uuid4(), merchant_name="NoNewVar")
    gen = ProductCatalogGenerator(
        merchant_contexts=[ctx],
        products_per_merchant=1,
        variants_per_product=1,
        seed=8,
    )
    gen.generate_catalog()
    product = gen._products[0]
    # Archive the product
    gen._archive_product(product)

    result = gen._add_variant_to_existing(product)
    assert result == []


def test_all_terminal_reflects_archived_state():
    ctx = MerchantContext(merchant_id=uuid.uuid4(), merchant_name="AllTerm")
    gen = ProductCatalogGenerator(
        merchant_contexts=[ctx],
        products_per_merchant=2,
        variants_per_product=1,
        seed=77,
    )
    gen.generate_catalog()
    assert not gen.all_terminal()

    for product in gen._products:
        gen._archive_product(product)

    assert gen.all_terminal()
    assert gen.tick() == []


# ---------------------------------------------------------------------------
# Non-negative inventory and valid Decimal prices
# ---------------------------------------------------------------------------


def test_initial_inventory_quantities_are_non_negative():
    gen = _make_generator(products_per_merchant=5, variants_per_product=4, seed=13)
    envelopes = gen.generate_catalog()
    for env in envelopes:
        if env.event_type == ProductEventType.PRODUCT_VARIANT_CREATED:
            qty = env.payload["inventory_quantity"]
            assert isinstance(qty, int), f"Expected int, got {type(qty)}"
            assert qty >= 0, f"Negative inventory: {qty}"


def test_initial_prices_are_valid_positive_decimals():
    gen = _make_generator(products_per_merchant=5, variants_per_product=4, seed=14)
    envelopes = gen.generate_catalog()
    for env in envelopes:
        if env.event_type == ProductEventType.PRODUCT_VARIANT_CREATED:
            # payload price is serialized as string by Decimal model_dump(mode="json")
            raw_price = env.payload["price"]
            price = Decimal(str(raw_price))
            assert price > Decimal("0"), f"Expected positive price, got {price}"


def test_tick_inventory_updates_stay_non_negative():
    ctx = MerchantContext(merchant_id=uuid.uuid4(), merchant_name="InvCheck")
    gen = ProductCatalogGenerator(
        merchant_contexts=[ctx],
        products_per_merchant=3,
        variants_per_product=3,
        seed=15,
    )
    gen.generate_catalog()

    for _ in range(100):
        gen.tick()

    for product in gen._products:
        for variant in product.variants:
            assert variant.inventory_quantity >= 0, (
                f"Negative inventory on variant {variant.variant_id}: {variant.inventory_quantity}"
            )


# ---------------------------------------------------------------------------
# Envelope contract
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# add_product is a bounded per-merchant tick opportunity, not a per-product action
# ---------------------------------------------------------------------------


def test_add_product_is_not_a_per_product_action():
    assert "add_product" not in _PRODUCT_ACTIONS


def test_new_product_opportunity_is_bounded_once_per_merchant_per_tick_regardless_of_product_count():
    ctx = MerchantContext(merchant_id=uuid.uuid4(), merchant_name="ManyProducts")
    gen = ProductCatalogGenerator(
        merchant_contexts=[ctx],
        products_per_merchant=10,
        variants_per_product=1,
        seed=1,
    )
    gen.generate_catalog()
    # Force every probabilistic branch to trigger; if add_product were a
    # per-product action this would create one product per existing product.
    gen._rng = _FakeAlwaysTriggerRng()

    envelopes = gen.tick()
    created = [e for e in envelopes if e.event_type == ProductEventType.PRODUCT_CREATED]
    assert len(created) == 1


def test_new_product_opportunity_is_independent_per_merchant():
    merchants = [
        MerchantContext(merchant_id=uuid.uuid4(), merchant_name="A"),
        MerchantContext(merchant_id=uuid.uuid4(), merchant_name="B"),
        MerchantContext(merchant_id=uuid.uuid4(), merchant_name="C"),
    ]
    gen = ProductCatalogGenerator(
        merchant_contexts=merchants,
        products_per_merchant=4,
        variants_per_product=1,
        seed=2,
    )
    gen.generate_catalog()
    gen._rng = _FakeAlwaysTriggerRng()

    envelopes = gen.tick()
    created = [e for e in envelopes if e.event_type == ProductEventType.PRODUCT_CREATED]
    assert len(created) == len(merchants)
    assert {e.merchant_id for e in created} == {m.merchant_id for m in merchants}


# ---------------------------------------------------------------------------
# Variant status is not among generated update fields
# ---------------------------------------------------------------------------


def test_status_is_not_an_updatable_variant_field():
    assert "status" not in _UPDATABLE_VARIANT_FIELDS


def test_update_variant_never_changes_status():
    ctx = MerchantContext(merchant_id=uuid.uuid4(), merchant_name="NoStatusUpdate")
    gen = ProductCatalogGenerator(
        merchant_contexts=[ctx],
        products_per_merchant=1,
        variants_per_product=5,
        seed=123,
    )
    gen.generate_catalog()
    product = gen._products[0]
    assert all(v.status == "active" for v in product.variants)

    for _ in range(200):
        for env in gen._update_variant(product):
            assert "status" not in env.payload["changed_values"]

    assert all(v.status == "active" for v in product.variants)


def test_all_generated_envelopes_are_product_event_envelopes():
    gen = _make_generator(products_per_merchant=3, variants_per_product=2, seed=99)
    envelopes = gen.generate_catalog()
    for _ in range(10):
        envelopes.extend(gen.tick())

    for env in envelopes:
        assert isinstance(env, ProductEventEnvelope)
        assert env.event_version == 1
        assert env.source == "product-generator"

