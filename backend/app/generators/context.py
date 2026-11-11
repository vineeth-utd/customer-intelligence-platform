"""Simulation context and clock abstraction for synthetic data generation.

Provides a unified time and random-number abstraction supporting both LIVE
(wall-clock) and HISTORICAL (stepped virtual time) generation modes.
"""

from datetime import datetime, timedelta, timezone
from enum import Enum
import random


class SimulationMode(str, Enum):
    LIVE = "live"
    HISTORICAL = "historical"


class SimulationContext:
    """Encapsulates simulated time, mode, and deterministic random number generator.

    In LIVE mode, `current_time` returns `datetime.now(timezone.utc)`.
    In HISTORICAL mode, `current_time` returns the simulated virtual timestamp,
    which advances deterministically as the simulation progresses.
    """

    def __init__(
        self,
        mode: SimulationMode = SimulationMode.LIVE,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        seed: int | None = None,
    ) -> None:
        self._mode = mode
        self._start_time = self._ensure_utc(start_time) if start_time else None
        self._end_time = self._ensure_utc(end_time) if end_time else None
        self._current_time: datetime = (
            self._start_time if self._start_time is not None else datetime.now(timezone.utc)
        )
        self._rng = random.Random(seed)

    @staticmethod
    def _ensure_utc(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    @property
    def mode(self) -> SimulationMode:
        return self._mode

    @property
    def start_time(self) -> datetime | None:
        return self._start_time

    @property
    def end_time(self) -> datetime | None:
        return self._end_time

    @property
    def rng(self) -> random.Random:
        return self._rng

    @property
    def current_time(self) -> datetime:
        if self._mode == SimulationMode.LIVE:
            return datetime.now(timezone.utc)
        return self._current_time

    def set_time(self, ts: datetime) -> None:
        if self._mode == SimulationMode.HISTORICAL:
            self._current_time = self._ensure_utc(ts)

    def advance_time(self, delta: timedelta) -> None:
        if self._mode == SimulationMode.HISTORICAL:
            self._current_time += delta

    def is_ended(self) -> bool:
        if self._mode == SimulationMode.HISTORICAL and self._end_time is not None:
            return self._current_time >= self._end_time
        return False

