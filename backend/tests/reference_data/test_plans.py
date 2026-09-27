from app.reference_data.plans import PLAN_CATALOG, BillingCycle, PlanKey


def test_all_plan_keys_present_in_catalog():
    assert set(PLAN_CATALOG.keys()) == set(PlanKey)


def test_catalog_prices_strictly_increase_with_plan_tier():
    ordered_prices = [entry.monthly_price for entry in sorted(PLAN_CATALOG.values(), key=lambda e: e.monthly_price)]
    assert ordered_prices == sorted(ordered_prices)
    assert len(set(ordered_prices)) == len(ordered_prices)


def test_billing_cycle_has_exactly_two_values():
    assert {cycle.value for cycle in BillingCycle} == {"monthly", "annual"}
