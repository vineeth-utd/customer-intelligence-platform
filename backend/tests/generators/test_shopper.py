import uuid
from decimal import Decimal
from app.generators.shopper import (
    CartItemState,
    MerchantCatalogContext,
    ProductContext,
    ShopperActivityState,
    ShopperBehaviorGenerator,
    ShopperState,
    VariantContext,
)
from app.schemas.events.event_types import ShopperEventType

def test_shopper_generator_state_machine_and_invariants():
    # Setup pure injected context
    merchant_id = uuid.uuid4()
    product_id = uuid.uuid4()
    variant_id = uuid.uuid4()
    
    ctx = MerchantCatalogContext(
        merchant_id=merchant_id,
        products=[
            ProductContext(
                product_id=product_id,
                product_name="P1",
                category="C1",
                variants=[VariantContext(variant_id=variant_id, price=Decimal("15.99"), inventory_quantity=10)]
            )
        ]
    )
    
    generator = ShopperBehaviorGenerator(shoppers_per_merchant=1, seed=42)
    generator.update_catalog([ctx])
    
    # Tick until a shopper is spawned
    envelopes = []
    while not generator._shoppers:
        envelopes.extend(generator.tick())
        
    assert len(generator._shoppers) == 1
    shopper = generator._shoppers[0]
    
    # Force shopper into BROWSING
    shopper.state = ShopperActivityState.BROWSING
    shopper.current_session_id = uuid.uuid4()
    
    # Force cart add
    add_envs = generator._add_to_cart(shopper)
    assert len(add_envs) == 1
    assert add_envs[0].event_type == ShopperEventType.ADD_TO_CART
    assert shopper.state == ShopperActivityState.IN_CART
    assert variant_id in shopper.cart
    assert shopper.cart[variant_id].quantity == 1
    
    # Force end session
    end_envs = generator._end_session(shopper)
    assert len(end_envs) == 1
    assert end_envs[0].event_type == ShopperEventType.SESSION_ENDED
    assert shopper.state == ShopperActivityState.IDLE
    assert shopper.current_session_id is None
    # Cart is preserved!
    assert variant_id in shopper.cart
    
    # Start new session
    start_envs = generator._start_session(shopper)
    assert len(start_envs) == 1
    assert start_envs[0].event_type == ShopperEventType.SESSION_STARTED
    # Transitions directly to IN_CART because cart is not empty
    assert shopper.state == ShopperActivityState.IN_CART
    assert shopper.current_session_id is not None
    
    # Complete purchase
    purch_envs = generator._complete_purchase(shopper)
    assert len(purch_envs) == 1
    assert purch_envs[0].event_type == ShopperEventType.PURCHASE_COMPLETED
    assert not shopper.cart # Cart is cleared
    
    # Inventory is decremented
    assert generator._variants[variant_id].inventory_quantity == 9
    
def test_shopper_generator_prunes_unavailable_cart_items():
    merchant_id = uuid.uuid4()
    product_id = uuid.uuid4()
    variant_id = uuid.uuid4()
    
    ctx = MerchantCatalogContext(
        merchant_id=merchant_id,
        products=[
            ProductContext(
                product_id=product_id,
                product_name="P1",
                category="C1",
                variants=[VariantContext(variant_id=variant_id, price=Decimal("10.00"), inventory_quantity=0)]
            )
        ]
    )
    generator = ShopperBehaviorGenerator(shoppers_per_merchant=1, seed=42)
    generator.update_catalog([ctx])
    
    generator._shoppers.append(ShopperState(
        shopper_id=uuid.uuid4(),
        merchant_id=merchant_id,
        cart={variant_id: CartItemState(product_id, variant_id, 1, Decimal("10.00"))}
    ))
    shopper = generator._shoppers[0]
    
    # Prune should remove it because inventory is 0
    generator._prune_cart(shopper)
    assert variant_id not in shopper.cart


def test_shopper_generator_save_for_later_and_wishlist_interactions():
    merchant_id = uuid.uuid4()
    product_id = uuid.uuid4()
    variant_id = uuid.uuid4()
    
    ctx = MerchantCatalogContext(
        merchant_id=merchant_id,
        products=[
            ProductContext(
                product_id=product_id,
                product_name="Test Product",
                category="Test Category",
                variants=[VariantContext(variant_id=variant_id, price=Decimal("15.99"), inventory_quantity=10)]
            )
        ]
    )
    generator = ShopperBehaviorGenerator(shoppers_per_merchant=1, seed=42)
    generator.update_catalog([ctx])
    
    shopper = ShopperState(shopper_id=uuid.uuid4(), merchant_id=merchant_id, current_session_id=uuid.uuid4())
    generator._shoppers.append(shopper)
    
    # Force add to save_for_later by setting rng to return > 0.7 for the branch
    # Let's just monkeypatch the _rng.random to return something predictable
    generator._rng.random = lambda: 0.8
    envs = generator._interact_wishlist_save_for_later(shopper)
    assert len(envs) == 1
    assert envs[0].event_type == ShopperEventType.SAVE_FOR_LATER_ADDED
    assert variant_id in shopper.save_for_later
    
    # Now force add to cart to pick from save_for_later
    generator._rng.random = lambda: 0.3 # < 0.4 branch for save_for_later
    cart_envs = generator._add_to_cart(shopper)
    assert len(cart_envs) == 1
    assert cart_envs[0].event_type == ShopperEventType.ADD_TO_CART
    assert variant_id not in shopper.save_for_later # Should be moved to cart
    assert variant_id in shopper.cart
    
def test_shopper_generator_search_derived_from_catalog():
    merchant_id = uuid.uuid4()
    product_id = uuid.uuid4()
    variant_id = uuid.uuid4()
    
    ctx = MerchantCatalogContext(
        merchant_id=merchant_id,
        products=[
            ProductContext(
                product_id=product_id,
                product_name="Magic Wand",
                category="Wizarding Gear",
                variants=[VariantContext(variant_id=variant_id, price=Decimal("15.99"), inventory_quantity=10)]
            )
        ]
    )
    generator = ShopperBehaviorGenerator(shoppers_per_merchant=1, seed=42)
    generator.update_catalog([ctx])
    
    shopper = ShopperState(shopper_id=uuid.uuid4(), merchant_id=merchant_id, current_session_id=uuid.uuid4())
    generator._shoppers.append(shopper)
    
    # Force use category
    generator._rng.random = lambda: 0.1
    envs = generator._search_product(shopper)
    assert envs[0].payload["search_query"] == "Wizarding Gear"
    
    # Force use product name part
    generator._rng.random = lambda: 0.9
    # rng.choice will pick from ["Magic", "Wand"].
    # Because we patched random, let's just assert it's one of them.
    # To be safe, restore real choice
    generator._rng.choice = lambda xs: xs[0] if isinstance(xs, list) else list(xs)[0]
    envs2 = generator._search_product(shopper)
    assert envs2[0].payload["search_query"] == "Magic"

def test_shopper_generator_session_lifecycle():
    merchant_id = uuid.uuid4()
    generator = ShopperBehaviorGenerator(shoppers_per_merchant=1, seed=42)
    generator.update_catalog([MerchantCatalogContext(merchant_id=merchant_id, products=[])])
    
    shopper = ShopperState(shopper_id=uuid.uuid4(), merchant_id=merchant_id)
    generator._shoppers.append(shopper)
    
    # Start session 1
    envs1 = generator._start_session(shopper)
    assert len(envs1) == 1
    assert envs1[0].event_type == ShopperEventType.SESSION_STARTED
    session1_id = envs1[0].session_id
    assert session1_id is not None
    assert shopper.current_session_id == session1_id
    
    # End session 1
    envs2 = generator._end_session(shopper)
    assert len(envs2) == 1
    assert envs2[0].event_type == ShopperEventType.SESSION_ENDED
    assert envs2[0].session_id == session1_id
    assert shopper.current_session_id is None
    
    # Start session 2
    envs3 = generator._start_session(shopper)
    assert len(envs3) == 1
    assert envs3[0].event_type == ShopperEventType.SESSION_STARTED
    session2_id = envs3[0].session_id
    assert session2_id is not None
    assert session2_id != session1_id
    assert shopper.current_session_id == session2_id

def test_shopper_generator_recommendations_causality():
    merchant_id = uuid.uuid4()
    product_id = uuid.uuid4()
    variant_id = uuid.uuid4()
    ctx = MerchantCatalogContext(
        merchant_id=merchant_id,
        products=[ProductContext(product_id=product_id, product_name="P", category="C", variants=[VariantContext(variant_id=variant_id, price=Decimal("10"), inventory_quantity=10)])]
    )
    generator = ShopperBehaviorGenerator(shoppers_per_merchant=1, seed=42)
    generator.update_catalog([ctx])
    
    shopper = ShopperState(shopper_id=uuid.uuid4(), merchant_id=merchant_id, current_session_id=uuid.uuid4())
    generator._shoppers.append(shopper)
    
    # Ensure no clicks if no views
    assert not shopper.session_recommendations_viewed
    generator._rng.random = lambda: 0.1 # Force click branch (r < 0.4)
    envs = generator._interact_recommendation(shopper)
    # Should fall through to VIEW if viewed is empty, actually logic: `if viewed and random < 0.4:` else `View`.
    # Let's check logic:
    assert len(envs) == 1
    assert envs[0].event_type == ShopperEventType.RECOMMENDATION_VIEWED
    assert variant_id in shopper.session_recommendations_viewed
    
    # Now that we have viewed, we can click it
    generator._rng.random = lambda: 0.1 # < 0.4 triggers click
    envs2 = generator._interact_recommendation(shopper)
    assert len(envs2) == 1
    assert envs2[0].event_type == ShopperEventType.RECOMMENDATION_CLICKED
    
    # Verify starting a new session clears the views
    generator._start_session(shopper)
    assert not shopper.session_recommendations_viewed

def test_shopper_generator_failed_cart_add_preserves_source():
    merchant_id = uuid.uuid4()
    product_id = uuid.uuid4()
    variant_id = uuid.uuid4()
    # Inventory is 0 so cart add fails
    ctx = MerchantCatalogContext(
        merchant_id=merchant_id,
        products=[ProductContext(product_id=product_id, product_name="P", category="C", variants=[VariantContext(variant_id=variant_id, price=Decimal("10"), inventory_quantity=0)])]
    )
    generator = ShopperBehaviorGenerator(shoppers_per_merchant=1, seed=42)
    generator.update_catalog([ctx])
    
    shopper = ShopperState(shopper_id=uuid.uuid4(), merchant_id=merchant_id, current_session_id=uuid.uuid4())
    shopper.wishlist.add(variant_id)
    generator._shoppers.append(shopper)
    
    # Try to add from wishlist
    generator._rng.random = lambda: 0.1 # < 0.2 means wishlist branch
    envs = generator._add_to_cart(shopper)
    assert len(envs) == 0 # Failed due to inventory
    # Verify wishlist is preserved!
    assert variant_id in shopper.wishlist

def test_shopper_generator_partial_cart_removal():
    merchant_id = uuid.uuid4()
    product_id = uuid.uuid4()
    variant_id = uuid.uuid4()
    ctx = MerchantCatalogContext(
        merchant_id=merchant_id,
        products=[ProductContext(product_id=product_id, product_name="P", category="C", variants=[VariantContext(variant_id=variant_id, price=Decimal("10"), inventory_quantity=10)])]
    )
    generator = ShopperBehaviorGenerator(shoppers_per_merchant=1, seed=42)
    generator.update_catalog([ctx])
    
    shopper = ShopperState(shopper_id=uuid.uuid4(), merchant_id=merchant_id, current_session_id=uuid.uuid4())
    shopper.cart[variant_id] = CartItemState(product_id, variant_id, 2, Decimal("10.00"))
    generator._shoppers.append(shopper)
    
    envs = generator._remove_from_cart(shopper)
    assert len(envs) == 1
    assert envs[0].event_type == ShopperEventType.REMOVE_FROM_CART
    assert envs[0].payload["quantity"] == 1
    # Cart item remains with quantity 1
    assert shopper.cart[variant_id].quantity == 1
    
    envs2 = generator._remove_from_cart(shopper)
    assert len(envs2) == 1
    assert envs2[0].event_type == ShopperEventType.REMOVE_FROM_CART
    # Cart item removed completely
    assert variant_id not in shopper.cart

def test_shopper_generator_checkout_and_purchase_totals():
    merchant_id = uuid.uuid4()
    product_id1 = uuid.uuid4()
    variant_id1 = uuid.uuid4()
    product_id2 = uuid.uuid4()
    variant_id2 = uuid.uuid4()
    ctx = MerchantCatalogContext(
        merchant_id=merchant_id,
        products=[
            ProductContext(product_id=product_id1, product_name="P1", category="C1", variants=[VariantContext(variant_id=variant_id1, price=Decimal("10.00"), inventory_quantity=10)]),
            ProductContext(product_id=product_id2, product_name="P2", category="C2", variants=[VariantContext(variant_id=variant_id2, price=Decimal("25.50"), inventory_quantity=5)])
        ]
    )
    generator = ShopperBehaviorGenerator(shoppers_per_merchant=1, seed=42)
    generator.update_catalog([ctx])
    
    shopper = ShopperState(shopper_id=uuid.uuid4(), merchant_id=merchant_id, current_session_id=uuid.uuid4())
    shopper.cart[variant_id1] = CartItemState(product_id1, variant_id1, 2, Decimal("10.00"))
    shopper.cart[variant_id2] = CartItemState(product_id2, variant_id2, 1, Decimal("25.50"))
    generator._shoppers.append(shopper)
    
    # Start checkout
    checkout_envs = generator._checkout_started(shopper)
    assert len(checkout_envs) == 1
    assert checkout_envs[0].event_type == ShopperEventType.CHECKOUT_STARTED
    # Total = 2*10.00 + 25.50 = 45.50
    assert Decimal(str(checkout_envs[0].payload["cart_value"])) == Decimal("45.50")
    
    # Complete purchase
    purchase_envs = generator._complete_purchase(shopper)
    assert len(purchase_envs) == 1
    assert purchase_envs[0].event_type == ShopperEventType.PURCHASE_COMPLETED
    assert Decimal(str(purchase_envs[0].payload["total_amount"])) == Decimal("45.50")
    assert len(purchase_envs[0].payload["items"]) == 2
    # Verify local inventory is decremented
    assert generator._variants[variant_id1].inventory_quantity == 8
    assert generator._variants[variant_id2].inventory_quantity == 4

def test_shopper_generator_anonymous_purchase_identity_persistence():
    merchant_id = uuid.uuid4()
    product_id = uuid.uuid4()
    variant_id = uuid.uuid4()
    ctx = MerchantCatalogContext(
        merchant_id=merchant_id,
        products=[ProductContext(product_id=product_id, product_name="P", category="C", variants=[VariantContext(variant_id=variant_id, price=Decimal("10"), inventory_quantity=10)])]
    )
    generator = ShopperBehaviorGenerator(shoppers_per_merchant=1, seed=42)
    generator.update_catalog([ctx])
    
    shopper = ShopperState(shopper_id=uuid.uuid4(), merchant_id=merchant_id, current_session_id=uuid.uuid4())
    shopper.cart[variant_id] = CartItemState(product_id, variant_id, 1, Decimal("10"))
    generator._shoppers.append(shopper)
    
    # Force remain anonymous
    generator._rng.random = lambda: 0.9
    purchase_envs = generator._complete_purchase(shopper)
    assert purchase_envs[0].payload.get("email") is None
    assert shopper.email is None
    
    # Add to cart again
    shopper.cart[variant_id] = CartItemState(product_id, variant_id, 1, Decimal("10"))
    
    # Force identification
    generator._rng.random = lambda: 0.1
    purchase_envs2 = generator._complete_purchase(shopper)
    assert purchase_envs2[0].payload["email"] is not None
    assert shopper.email == purchase_envs2[0].payload["email"]
    
    # Ensure later sessions retain email
    start_envs = generator._start_session(shopper)
    assert start_envs[0].payload["email"] == shopper.email

def test_shopper_generator_catalog_reconciliation_preserves_state_and_prunes_cart():
    merchant_id = uuid.uuid4()
    product_id1 = uuid.uuid4()
    variant_id1 = uuid.uuid4() # stays active
    product_id2 = uuid.uuid4()
    variant_id2 = uuid.uuid4() # becomes unavailable
    product_id3 = uuid.uuid4()
    variant_id3 = uuid.uuid4() # drops from catalog
    
    ctx1 = MerchantCatalogContext(
        merchant_id=merchant_id,
        products=[
            ProductContext(product_id=product_id1, product_name="P1", category="C1", variants=[VariantContext(variant_id=variant_id1, price=Decimal("10"), inventory_quantity=10)]),
            ProductContext(product_id=product_id2, product_name="P2", category="C2", variants=[VariantContext(variant_id=variant_id2, price=Decimal("20"), inventory_quantity=10)]),
            ProductContext(product_id=product_id3, product_name="P3", category="C3", variants=[VariantContext(variant_id=variant_id3, price=Decimal("30"), inventory_quantity=10)])
        ]
    )
    generator = ShopperBehaviorGenerator(shoppers_per_merchant=1, seed=42)
    generator.update_catalog([ctx1])
    
    shopper = ShopperState(shopper_id=uuid.uuid4(), merchant_id=merchant_id, current_session_id=uuid.uuid4())
    shopper.wishlist.add(variant_id3)
    shopper.save_for_later.add(variant_id3)
    shopper.cart[variant_id1] = CartItemState(product_id1, variant_id1, 1, Decimal("10"))
    shopper.cart[variant_id2] = CartItemState(product_id2, variant_id2, 1, Decimal("20"))
    shopper.cart[variant_id3] = CartItemState(product_id3, variant_id3, 1, Decimal("30"))
    generator._shoppers.append(shopper)
    
    # Now reconcile catalog where var2 has 0 inventory, and var3 is completely gone
    ctx2 = MerchantCatalogContext(
        merchant_id=merchant_id,
        products=[
            ProductContext(product_id=product_id1, product_name="P1", category="C1", variants=[VariantContext(variant_id=variant_id1, price=Decimal("10"), inventory_quantity=10)]),
            ProductContext(product_id=product_id2, product_name="P2", category="C2", variants=[VariantContext(variant_id=variant_id2, price=Decimal("20"), inventory_quantity=0)])
        ]
    )
    generator.update_catalog([ctx2])
    
    # State is preserved
    assert variant_id3 in shopper.wishlist
    assert variant_id3 in shopper.save_for_later
    assert variant_id2 in shopper.cart
    assert variant_id3 in shopper.cart
    
    # Now checkout should prune unavailable cart entries
    generator._checkout_started(shopper)
    assert variant_id1 in shopper.cart
    assert variant_id2 not in shopper.cart
    assert variant_id3 not in shopper.cart

