"""Money helpers using Decimal with BRL precision rules."""

from decimal import ROUND_HALF_UP, Decimal

MONEY_PRECISION = Decimal("0.01")


def quantize_money(value: Decimal) -> Decimal:
    """Return value rounded to two decimal places with HALF_UP strategy."""

    return value.quantize(MONEY_PRECISION, rounding=ROUND_HALF_UP)


def parse_money(value: str) -> Decimal:
    """Parse and normalize input money string into Decimal."""

    return quantize_money(Decimal(value))


def format_money(value: Decimal) -> str:
    """Render money as string with exactly two decimal places."""

    return f"{quantize_money(value):.2f}"
