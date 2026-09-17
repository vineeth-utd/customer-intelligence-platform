from app.generators.merchant import MerchantLifecycleGenerator
from app.schemas.events.envelope import MerchantEventEnvelope
from app.schemas.events.event_types import MerchantEventType


def _event_type_sequence(generator: MerchantLifecycleGenerator, ticks: int) -> list[str]:
    sequence = [envelope.event_type.value for envelope in generator.generate_population()]
    for _ in range(ticks):
        sequence.extend(envelope.event_type.value for envelope in generator.tick())
    return sequence


def test_population_emits_created_installed_subscribed_per_merchant():
    generator = MerchantLifecycleGenerator(population_size=3, seed=42)
    envelopes = generator.generate_population()

    assert len(envelopes) == 9
    for index in range(3):
        chunk = envelopes[index * 3 : index * 3 + 3]
        assert [envelope.event_type for envelope in chunk] == [
            MerchantEventType.MERCHANT_CREATED,
            MerchantEventType.APP_INSTALLED,
            MerchantEventType.SUBSCRIPTION_STARTED,
        ]
        assert chunk[0].merchant_id == chunk[1].merchant_id == chunk[2].merchant_id


def test_fresh_instances_never_reuse_merchant_ids():
    first = MerchantLifecycleGenerator(population_size=5, seed=1).generate_population()
    second = MerchantLifecycleGenerator(population_size=5, seed=1).generate_population()

    first_ids = {envelope.merchant_id for envelope in first}
    second_ids = {envelope.merchant_id for envelope in second}
    assert first_ids.isdisjoint(second_ids)


def test_same_seed_produces_identical_event_type_sequence():
    sequence_a = _event_type_sequence(MerchantLifecycleGenerator(population_size=5, seed=7), ticks=30)
    sequence_b = _event_type_sequence(MerchantLifecycleGenerator(population_size=5, seed=7), ticks=30)
    assert sequence_a == sequence_b


def test_different_seeds_can_diverge():
    sequence_a = _event_type_sequence(MerchantLifecycleGenerator(population_size=5, seed=7), ticks=30)
    sequence_c = _event_type_sequence(MerchantLifecycleGenerator(population_size=5, seed=123), ticks=30)
    assert sequence_a != sequence_c


def test_uninstall_never_precedes_cancellation_for_the_same_merchant():
    generator = MerchantLifecycleGenerator(population_size=10, seed=1)
    generator.generate_population()

    cancelled_merchant_ids: set = set()
    for _ in range(200):
        for envelope in generator.tick():
            if envelope.event_type == MerchantEventType.APP_UNINSTALLED:
                assert envelope.merchant_id in cancelled_merchant_ids
            if envelope.event_type == MerchantEventType.SUBSCRIPTION_CANCELLED:
                cancelled_merchant_ids.add(envelope.merchant_id)


def test_terminal_merchant_stops_producing_further_events():
    generator = MerchantLifecycleGenerator(population_size=1, seed=99)
    generator.generate_population()

    reached_terminal = False
    for _ in range(500):
        envelopes = generator.tick()
        if any(envelope.event_type == MerchantEventType.APP_UNINSTALLED for envelope in envelopes):
            reached_terminal = True
            break

    assert reached_terminal
    assert generator.all_terminal()
    assert generator.tick() == []


def test_tick_returns_valid_merchant_event_envelopes():
    generator = MerchantLifecycleGenerator(population_size=8, seed=5)
    generator.generate_population()

    for _ in range(20):
        for envelope in generator.tick():
            assert isinstance(envelope, MerchantEventEnvelope)
            assert envelope.event_version == 1


def test_configuration_update_is_reflected_in_merchant_state():
    generator = MerchantLifecycleGenerator(population_size=1, seed=5)
    generator.generate_population()
    state = generator._merchants[0]

    observed_fields = set()
    for _ in range(50):
        envelopes = generator._perform_action(state, "config_update")
        if not envelopes:
            continue
        field_name, new_value = next(iter(envelopes[0].payload["changed_values"].items()))
        observed_fields.add(field_name)
        if field_name in ("timezone", "country"):
            assert getattr(state, field_name) == new_value

    assert {"timezone", "country"}.issubset(observed_fields)
