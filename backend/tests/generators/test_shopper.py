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

