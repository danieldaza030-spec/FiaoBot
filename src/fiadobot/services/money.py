"""Helpers for consistent monetary calculations."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

MONEY_QUANTUM = Decimal("0.01")


def normalize_money(value: Decimal) -> Decimal:
    """Round a decimal value to the money precision used by the system.

    Args:
        value: Decimal value to normalize to two decimal places.

    Returns:
        The value rounded using half-up currency rules.
    """

    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def sum_money(values: Iterable[Decimal]) -> Decimal:
    """Sum monetary values and normalize the final total.

    Args:
        values: Iterable of decimal values to add together.

    Returns:
        The normalized sum of all values in the iterable.
    """

    total = Decimal("0.00")
    for value in values:
        total += value

    return normalize_money(total)
