from datetime import datetime, timedelta, timezone

from app.generators.context import SimulationContext, SimulationMode


def test_simulation_context_live_mode():
    ctx = SimulationContext(mode=SimulationMode.LIVE)
    assert ctx.mode == SimulationMode.LIVE
    assert ctx.is_ended() is False

    before = datetime.now(timezone.utc)
    curr = ctx.current_time
    after = datetime.now(timezone.utc)
    assert before <= curr <= after

    # Mutating virtual time in LIVE mode does not alter current_time
    ctx.set_time(datetime(2020, 1, 1, tzinfo=timezone.utc))
    assert ctx.current_time >= before


def test_simulation_context_historical_mode():
    start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 1, 31, 23, 59, 59, tzinfo=timezone.utc)
    ctx = SimulationContext(mode=SimulationMode.HISTORICAL, start_time=start, end_time=end, seed=42)

    assert ctx.mode == SimulationMode.HISTORICAL
    assert ctx.start_time == start
    assert ctx.end_time == end
    assert ctx.current_time == start
    assert ctx.is_ended() is False

    # Advance time
    ctx.advance_time(timedelta(days=10))
    assert ctx.current_time == start + timedelta(days=10)
    assert ctx.is_ended() is False

    # Set time to end
    ctx.set_time(end)
    assert ctx.current_time == end
    assert ctx.is_ended() is True

    # Advance past end
    ctx.advance_time(timedelta(seconds=1))
    assert ctx.is_ended() is True


def test_simulation_context_naive_datetime_localized():
    start_naive = datetime(2026, 5, 1, 12, 0, 0)
    ctx = SimulationContext(mode=SimulationMode.HISTORICAL, start_time=start_naive)
    assert ctx.current_time.tzinfo == timezone.utc


def test_simulation_context_rng_determinism():
    ctx_1 = SimulationContext(seed=123)
    ctx_2 = SimulationContext(seed=123)
    ctx_3 = SimulationContext(seed=999)

    seq_1 = [ctx_1.rng.random() for _ in range(20)]
    seq_2 = [ctx_2.rng.random() for _ in range(20)]
    seq_3 = [ctx_3.rng.random() for _ in range(20)]

    assert seq_1 == seq_2
    assert seq_1 != seq_3

