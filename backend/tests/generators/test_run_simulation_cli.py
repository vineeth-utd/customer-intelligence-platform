from datetime import date
from unittest.mock import AsyncMock, patch
import pytest

from scripts.run_simulation import _parse_args, _run


def test_parse_args_defaults(monkeypatch):
    test_args = [
        "prog",
        "--start-date",
        "2026-08-01",
        "--end-date",
        "2026-11-01",
    ]
    monkeypatch.setattr("sys.argv", test_args)
    args = _parse_args()

    assert args.mode == "historical"
    assert args.start_date == date(2026, 8, 1)
    assert args.end_date == date(2026, 11, 1)
    assert args.seed == 42
    assert args.merchants == 5
    assert args.products_per_merchant == 8
    assert args.variants_per_product == 3
    assert args.shoppers_per_merchant == 50
    assert args.campaigns_per_merchant == 3


def test_parse_args_custom(monkeypatch):
    test_args = [
        "prog",
        "--start-date",
        "2026-01-01",
        "--end-date",
        "2026-06-01",
        "--seed",
        "999",
        "--merchants",
        "2",
        "--products-per-merchant",
        "4",
        "--variants-per-product",
        "2",
        "--shoppers-per-merchant",
        "10",
        "--campaigns-per-merchant",
        "1",
    ]
    monkeypatch.setattr("sys.argv", test_args)
    args = _parse_args()

    assert args.seed == 999
    assert args.merchants == 2
    assert args.products_per_merchant == 4


@pytest.mark.asyncio
async def test_run_simulation_pipeline_publishes_to_kafka(monkeypatch):
    test_args = [
        "prog",
        "--start-date",
        "2026-09-01",
        "--end-date",
        "2026-10-01",
        "--seed",
        "123",
        "--merchants",
        "1",
        "--products-per-merchant",
        "2",
        "--variants-per-product",
        "2",
        "--shoppers-per-merchant",
        "5",
        "--campaigns-per-merchant",
        "1",
    ]
    monkeypatch.setattr("sys.argv", test_args)
    args = _parse_args()

    with patch("scripts.run_simulation.event_producer") as mock_producer:
        mock_producer.start = AsyncMock()
        mock_producer.stop = AsyncMock()
        mock_producer.publish = AsyncMock()

        await _run(args)

        assert mock_producer.start.awaited
        assert mock_producer.stop.awaited
        assert mock_producer.publish.await_count > 0

