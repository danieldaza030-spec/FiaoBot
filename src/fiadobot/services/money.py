"""Helpers for consistent monetary calculations."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

MONEY_QUANTUM = Decimal("0.01")


def normalize_money(value: Decimal) -> Decimal:
    """Round a Decimal to the two decimal places used across the system."""

    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def sum_money(values: Iterable[Decimal]) -> Decimal:
    """Sum an iterable of Decimal values and normalize the result."""

    total = Decimal("0.00")
    for value in values:
        total += value

    return normalize_money(total)
