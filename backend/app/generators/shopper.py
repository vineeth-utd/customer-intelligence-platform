"""Deterministic, in-memory Shopper behavior simulator.

Holds no database, Kafka, service, DAL, async, or cadence dependencies.
Builds validated ShopperEventEnvelope objects for a caller to publish.
"""

import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from app.schemas.events.envelope import ShopperEventEnvelope
from app.schemas.events.event_types import ShopperEventType
from app.schemas.events.payloads.shopper import (
    AddToCartPayload,
    CartItem,
    CheckoutStartedPayload,
    OrderItemPayload,
    ProductSearchedPayload,
    ProductViewedPayload,
    PurchaseCompletedPayload,
    RecommendationClickedPayload,
    RecommendationViewedPayload,
    RemoveFromCartPayload,
    SaveForLaterAddedPayload,
    SaveForLaterRemovedPayload,
    SessionEndedPayload,
    SessionStartedPayload,
    WishlistAddedPayload,
    WishlistRemovedPayload,
)

class ShopperActivityState(str, Enum):
    IDLE = "IDLE"
    BROWSING = "BROWSING"
    IN_CART = "IN_CART"
    CHECKOUT = "CHECKOUT"

@dataclass
class VariantContext:
    variant_id: uuid.UUID
    price: Decimal
    inventory_quantity: int

@dataclass
class ProductContext:
    product_id: uuid.UUID
    product_name: str
    category: str | None
    variants: list[VariantContext]

@dataclass
class MerchantCatalogContext:
    merchant_id: uuid.UUID
    products: list[ProductContext]

@dataclass
class CartItemState:
    product_id: uuid.UUID
    variant_id: uuid.UUID
    quantity: int
    unit_price: Decimal

@dataclass
class ShopperState:
    shopper_id: uuid.UUID
    merchant_id: uuid.UUID
    email: str | None = None
    current_session_id: uuid.UUID | None = None
    state: ShopperActivityState = ShopperActivityState.IDLE
    wishlist: set[uuid.UUID] = field(default_factory=set)        # variant_ids
    save_for_later: set[uuid.UUID] = field(default_factory=set)  # variant_ids
    cart: dict[uuid.UUID, CartItemState] = field(default_factory=dict) # variant_id -> item
    purchased_variant_ids: set[uuid.UUID] = field(default_factory=set)
    session_recommendations_viewed: set[uuid.UUID] = field(default_factory=set) # variant_ids

class ShopperBehaviorGenerator:
    """Simulates shopper lifecycle across multiple sessions.
    
    Operates on a pure, injected catalog context. Context can be reconciled
    to reflect updates without recreating the generator or dropping shopper state.
    """

    def __init__(
        self,
        shoppers_per_merchant: int = 50,
        seed: int | None = None,
    ) -> None:
        self._rng = random.Random(seed)
        self._shoppers_per_merchant = shoppers_per_merchant
        self._shoppers: list[ShopperState] = []
        
        # Lookups to quickly check validity / price during simulation
        self._merchants: set[uuid.UUID] = set()
        self._active_products: dict[uuid.UUID, list[uuid.UUID]] = {} # merchant_id -> product_ids
        self._products: dict[uuid.UUID, ProductContext] = {}         # product_id -> context
        self._variants: dict[uuid.UUID, VariantContext] = {}         # variant_id -> context
        self._variant_to_product: dict[uuid.UUID, uuid.UUID] = {}    # variant_id -> product_id

    def update_catalog(self, catalogs: list[MerchantCatalogContext]) -> None:
        """Reconciles the generator's working catalog context.
        
        Historical shopper state referencing missing/archived variants remains
        in memory, but active actions (like checking out a missing variant) will
        gracefully prune it to reflect reality.
        """
        self._merchants.clear()
        self._active_products.clear()
        self._products.clear()
        self._variants.clear()
        self._variant_to_product.clear()

        for catalog in catalogs:
            self._merchants.add(catalog.merchant_id)
            self._active_products[catalog.merchant_id] = []
            for prod in catalog.products:
                if not prod.variants:
                    continue  # Ignore products without variants
                self._active_products[catalog.merchant_id].append(prod.product_id)
                self._products[prod.product_id] = prod
                for var in prod.variants:
                    self._variants[var.variant_id] = var
                    self._variant_to_product[var.variant_id] = prod.product_id

    def tick(self) -> list[ShopperEventEnvelope]:
        """Advances the simulation by one step for all active shoppers."""
        envelopes: list[ShopperEventEnvelope] = []
        if not self._merchants:
            return envelopes

        # Spawn new shoppers up to the bounded population limit
        current_shoppers_by_merchant = {m: 0 for m in self._merchants}
        for s in self._shoppers:
            if s.merchant_id in current_shoppers_by_merchant:
                current_shoppers_by_merchant[s.merchant_id] += 1
                
        for merchant_id in sorted(self._merchants): # Deterministic iteration
            if current_shoppers_by_merchant[merchant_id] < self._shoppers_per_merchant:
                if self._rng.random() < 0.1: # 10% chance to spawn a new shopper per tick
                    self._shoppers.append(ShopperState(
                        shopper_id=uuid.uuid4(),
                        merchant_id=merchant_id,
                    ))

        # Evaluate each shopper's state transition
        for shopper in self._shoppers:
            # Skip shoppers whose merchant was dropped from the catalog
            if shopper.merchant_id not in self._merchants:
                continue

            action = self._determine_next_action(shopper)
            if action:
                envelopes.extend(action(shopper))

        return envelopes

    def _determine_next_action(self, shopper: ShopperState):
        """Returns the transition method to invoke based on current state probabilities."""
        r = self._rng.random()
        
        if shopper.state == ShopperActivityState.IDLE:
            if r < 0.2:
                return self._start_session
            return None
            
        elif shopper.state == ShopperActivityState.BROWSING:
            if r < 0.1: return self._end_session
            if r < 0.3: return self._search_product
            if r < 0.6: return self._view_product
            if r < 0.7: return self._interact_recommendation
            if r < 0.8: return self._interact_wishlist_save_for_later
            if r < 0.95: return self._add_to_cart
            return self._checkout_started # Direct from browse if cart is not empty

        elif shopper.state == ShopperActivityState.IN_CART:
            if r < 0.1: return self._end_session
            if r < 0.3: return self._view_product
            if r < 0.5: return self._add_to_cart
            if r < 0.6: return self._remove_from_cart
            return self._checkout_started
            
        elif shopper.state == ShopperActivityState.CHECKOUT:
            if r < 0.2: return self._end_session # Abandon checkout
            return self._complete_purchase
            
        return None

    # --- Actions ---

    def _start_session(self, shopper: ShopperState) -> list[ShopperEventEnvelope]:
        shopper.current_session_id = uuid.uuid4()
        shopper.session_recommendations_viewed.clear()
        
        # If cart has items, maybe jump to IN_CART directly
        if shopper.cart:
            shopper.state = ShopperActivityState.IN_CART
        else:
            shopper.state = ShopperActivityState.BROWSING
            
        return [self._build_envelope(
            shopper, 
            ShopperEventType.SESSION_STARTED, 
            SessionStartedPayload(
                referrer=self._rng.choice(["google.com", "facebook.com", "direct", None]),
                email=shopper.email
            )
        )]

    def _end_session(self, shopper: ShopperState) -> list[ShopperEventEnvelope]:
        shopper.state = ShopperActivityState.IDLE
        # session_id stays attached for the ENDED event
        env = self._build_envelope(shopper, ShopperEventType.SESSION_ENDED, SessionEndedPayload())
        shopper.current_session_id = None
        return [env]

    def _search_product(self, shopper: ShopperState) -> list[ShopperEventEnvelope]:
        products = self._active_products.get(shopper.merchant_id, [])
        if not products:
            return []
        prod_id = self._rng.choice(products)
        prod_ctx = self._products[prod_id]
        
        # Search by product name or category
        if prod_ctx.category and self._rng.random() < 0.3:
            search_query = prod_ctx.category
        else:
            # Maybe just a partial word from the product name
            words = prod_ctx.product_name.split()
            search_query = self._rng.choice(words) if words else prod_ctx.product_name

        return [self._build_envelope(
            shopper, 
            ShopperEventType.PRODUCT_SEARCHED, 
            ProductSearchedPayload(search_query=search_query, result_count=self._rng.randint(1, 10))
        )]

    def _view_product(self, shopper: ShopperState) -> list[ShopperEventEnvelope]:
        products = self._active_products.get(shopper.merchant_id, [])
        if not products:
            return []
        prod_id = self._rng.choice(products)
        variants = self._products[prod_id].variants
        var_id = self._rng.choice(variants).variant_id if variants else None
        
        return [self._build_envelope(
            shopper, 
            ShopperEventType.PRODUCT_VIEWED, 
            ProductViewedPayload(product_id=prod_id, variant_id=var_id)
        )]

    def _interact_recommendation(self, shopper: ShopperState) -> list[ShopperEventEnvelope]:
        # Either view a new recommendation, or click a previously viewed one in this session
        products = self._active_products.get(shopper.merchant_id, [])
        if not products:
            return []
            
        if shopper.session_recommendations_viewed and self._rng.random() < 0.4:
            # Click
            var_id = self._rng.choice(list(shopper.session_recommendations_viewed))
            prod_id = self._variant_to_product.get(var_id)
            if not prod_id:
                return [] # Variant dropped from catalog
            return [self._build_envelope(
                shopper, 
                ShopperEventType.RECOMMENDATION_CLICKED, 
                RecommendationClickedPayload(product_id=prod_id, variant_id=var_id)
            )]
        else:
            # View
            prod_id = self._rng.choice(products)
            variants = self._products[prod_id].variants
            if not variants:
                return []
            var_id = self._rng.choice(variants).variant_id
            shopper.session_recommendations_viewed.add(var_id)
            return [self._build_envelope(
                shopper, 
                ShopperEventType.RECOMMENDATION_VIEWED, 
                RecommendationViewedPayload(product_id=prod_id, variant_id=var_id)
            )]

    def _interact_wishlist_save_for_later(self, shopper: ShopperState) -> list[ShopperEventEnvelope]:
        r = self._rng.random()
        
        # 1. Remove from Wishlist
        if shopper.wishlist and r < 0.2:
            var_id = self._rng.choice(list(shopper.wishlist))
            shopper.wishlist.remove(var_id)
            prod_id = self._variant_to_product.get(var_id)
            if prod_id:
                return [self._build_envelope(shopper, ShopperEventType.WISHLIST_REMOVED, WishlistRemovedPayload(product_id=prod_id, variant_id=var_id))]

        # 2. Remove from Save For Later
        elif shopper.save_for_later and r < 0.4:
            var_id = self._rng.choice(list(shopper.save_for_later))
            shopper.save_for_later.remove(var_id)
            prod_id = self._variant_to_product.get(var_id)
            if prod_id:
                return [self._build_envelope(shopper, ShopperEventType.SAVE_FOR_LATER_REMOVED, SaveForLaterRemovedPayload(product_id=prod_id, variant_id=var_id))]

        # 3. Add to Wishlist or Save For Later
        else:
            products = self._active_products.get(shopper.merchant_id, [])
            if not products:
                return []
            prod_id = self._rng.choice(products)
            variants = self._products[prod_id].variants
            if not variants:
                return []
            var_id = self._rng.choice(variants).variant_id
            
            if r < 0.7:
                shopper.wishlist.add(var_id)
                return [self._build_envelope(shopper, ShopperEventType.WISHLIST_ADDED, WishlistAddedPayload(product_id=prod_id, variant_id=var_id))]
            else:
                shopper.save_for_later.add(var_id)
                return [self._build_envelope(shopper, ShopperEventType.SAVE_FOR_LATER_ADDED, SaveForLaterAddedPayload(product_id=prod_id, variant_id=var_id))]
        return []

    def _add_to_cart(self, shopper: ShopperState) -> list[ShopperEventEnvelope]:
        var_id = None
        source_list = None
        r = self._rng.random()
        
        # 1. From wishlist
        if shopper.wishlist and r < 0.2:
            var_id = self._rng.choice(list(shopper.wishlist))
            source_list = shopper.wishlist
            
        # 2. From save for later
        elif shopper.save_for_later and r < 0.4:
            var_id = self._rng.choice(list(shopper.save_for_later))
            source_list = shopper.save_for_later
            
        # 3. New browse
        if not var_id:
            products = self._active_products.get(shopper.merchant_id, [])
            if not products:
                return []
            prod_id = self._rng.choice(products)
            variants = self._products[prod_id].variants
            if not variants:
                return []
            var_ctx = self._rng.choice(variants)
            var_id = var_ctx.variant_id
            
        # Check if variant still exists in catalog
        var_ctx = self._variants.get(var_id)
        if not var_ctx:
            return []
            
        prod_id = self._variant_to_product[var_id]
        
        # Check inventory
        existing_qty = shopper.cart.get(var_id, CartItemState(prod_id, var_id, 0, var_ctx.price)).quantity
        if var_ctx.inventory_quantity > existing_qty:
            qty_to_add = 1 # Keep it simple
            
            if var_id not in shopper.cart:
                shopper.cart[var_id] = CartItemState(prod_id, var_id, qty_to_add, var_ctx.price)
            else:
                shopper.cart[var_id].quantity += qty_to_add
                
            # Now that it's successfully added, remove it from the source list if it came from one
            if source_list is not None and var_id in source_list:
                source_list.remove(var_id)

            shopper.state = ShopperActivityState.IN_CART
            return [self._build_envelope(
                shopper,
                ShopperEventType.ADD_TO_CART,
                AddToCartPayload(product_id=prod_id, variant_id=var_id, quantity=qty_to_add, unit_price=var_ctx.price)
            )]
        return []

    def _remove_from_cart(self, shopper: ShopperState) -> list[ShopperEventEnvelope]:
        if not shopper.cart:
            shopper.state = ShopperActivityState.BROWSING
            return []
            
        var_id = self._rng.choice(list(shopper.cart.keys()))
        item = shopper.cart[var_id]
        
        # Remove 1
        item.quantity -= 1
        payload = RemoveFromCartPayload(product_id=item.product_id, variant_id=item.variant_id, quantity=1)
        
        if item.quantity <= 0:
            del shopper.cart[var_id]
            if not shopper.cart:
                shopper.state = ShopperActivityState.BROWSING
                
        return [self._build_envelope(shopper, ShopperEventType.REMOVE_FROM_CART, payload)]

    def _checkout_started(self, shopper: ShopperState) -> list[ShopperEventEnvelope]:
        # Validate cart against current catalog context, pruning unavailable items
        self._prune_cart(shopper)
        
        if not shopper.cart:
            shopper.state = ShopperActivityState.BROWSING
            return []
            
        shopper.state = ShopperActivityState.CHECKOUT
        
        cart_items = []
        cart_value = Decimal("0.00")
        for item in shopper.cart.values():
            cart_items.append(CartItem(
                product_id=item.product_id,
                variant_id=item.variant_id,
                quantity=item.quantity,
                unit_price=item.unit_price
            ))
            cart_value += item.unit_price * Decimal(item.quantity)
            
        # Optional probabilistic identification
        if not shopper.email and self._rng.random() < 0.4:
            shopper.email = f"shopper_{shopper.shopper_id.hex[:6]}@synthetic.com"
            
        return [self._build_envelope(
            shopper,
            ShopperEventType.CHECKOUT_STARTED,
            CheckoutStartedPayload(cart_value=cart_value, items=cart_items, email=shopper.email)
        )]

    def _complete_purchase(self, shopper: ShopperState) -> list[ShopperEventEnvelope]:
        self._prune_cart(shopper)
        if not shopper.cart:
            shopper.state = ShopperActivityState.BROWSING
            return []
            
        order_items = []
        total_amount = Decimal("0.00")
        
        for item in shopper.cart.values():
            order_items.append(OrderItemPayload(
                product_id=item.product_id,
                variant_id=item.variant_id,
                quantity=item.quantity,
                unit_price=item.unit_price
            ))
            total_amount += item.unit_price * Decimal(item.quantity)
            
            # Update local inventory state to prevent overselling
            var_ctx = self._variants[item.variant_id]
            var_ctx.inventory_quantity = max(0, var_ctx.inventory_quantity - item.quantity)
            
            shopper.purchased_variant_ids.add(item.variant_id)
            
        order_id = uuid.uuid4()
        
        if not shopper.email and self._rng.random() < 0.5:
             shopper.email = f"shopper_{shopper.shopper_id.hex[:6]}@synthetic.com"
             
        env = self._build_envelope(
            shopper,
            ShopperEventType.PURCHASE_COMPLETED,
            PurchaseCompletedPayload(order_id=order_id, total_amount=total_amount, items=order_items, email=shopper.email)
        )
        
        shopper.cart.clear()
        shopper.state = ShopperActivityState.BROWSING
        return [env]

    def _prune_cart(self, shopper: ShopperState) -> None:
        """Removes items from cart if they are no longer in the catalog or out of stock."""
        invalid_vars = []
        for var_id, item in shopper.cart.items():
            var_ctx = self._variants.get(var_id)
            if not var_ctx or var_ctx.inventory_quantity < item.quantity:
                invalid_vars.append(var_id)
        for var_id in invalid_vars:
            del shopper.cart[var_id]

    def _build_envelope(self, shopper: ShopperState, event_type: ShopperEventType, payload: object) -> ShopperEventEnvelope:
        return ShopperEventEnvelope(
            event_id=uuid.uuid4(),
            event_type=event_type,
            event_version=1,
            event_timestamp=datetime.now(timezone.utc),
            merchant_id=shopper.merchant_id,
            shopper_id=shopper.shopper_id,
            session_id=shopper.current_session_id, # Validated non-null by caller state (except if misconfigured)
            payload=payload.model_dump(mode="json"),
            source="shopper-generator"
        )
