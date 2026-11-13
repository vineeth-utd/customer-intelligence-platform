from decimal import Decimal
from typing import Optional, Union


def calculate_period_growth(
    current: Optional[Union[Decimal, int, float]],
    previous: Optional[Union[Decimal, int, float]],
    precision: int = 2,
) -> Optional[Decimal]:
    """
    Calculate period-over-period percentage growth using:
    ((current - previous) / previous) * 100

    Deterministic zero baseline rules:
    - previous is None or current is None -> None
    - previous <= 0 and current == 0 -> None (no baseline/activity)
    - previous <= 0 and current > 0 -> None (cannot fabricate infinite growth)
    - previous > 0 and current == 0 -> -100.00% (total loss of metric)
    - previous > 0 and current > 0 -> round(((current - previous) / previous) * 100, precision)
    """
    if current is None or previous is None:
        return None

    curr_dec = Decimal(str(current))
    prev_dec = Decimal(str(previous))

    if prev_dec <= Decimal("0"):
        return None

    growth = ((curr_dec - prev_dec) / prev_dec) * Decimal("100.0")
    return round(growth, precision)

