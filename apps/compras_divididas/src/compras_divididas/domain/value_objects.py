"""Domain value objects for money and period handling."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True, slots=True)
class MoneyBRL:
    """Represents a BRL amount in integer cents."""

    cents: int

    def __post_init__(self) -> None:
        if not isinstance(self.cents, int):
            raise TypeError("Money cents must be an integer")

    @classmethod
    def from_decimal(cls, amount: Decimal) -> MoneyBRL:
        """Create a money value from decimal BRL amount."""
        quantized = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        cents = int(quantized * 100)
        return cls(cents=cents)

    @classmethod
    def zero(cls) -> MoneyBRL:
        """Return a zero BRL amount."""
        return cls(cents=0)

    def __add__(self, other: MoneyBRL) -> MoneyBRL:
        return MoneyBRL(cents=self.cents + other.cents)

    def __sub__(self, other: MoneyBRL) -> MoneyBRL:
        return MoneyBRL(cents=self.cents - other.cents)

    def absolute(self) -> MoneyBRL:
        """Return the absolute money amount."""
        return MoneyBRL(cents=abs(self.cents))

    def to_brl(self) -> str:
        """Format amount as BRL string."""
        value = Decimal(self.cents) / Decimal(100)
        normalized = f"{value:.2f}".replace(".", ",")
        return f"R$ {normalized}"


@dataclass(frozen=True, slots=True)
class Period:
    """Represents a calendar period for monthly closure."""

    year: int
    month: int

    def __post_init__(self) -> None:
        if not 1 <= self.month <= 12:
            raise ValueError("Month must be between 1 and 12")
        if self.year < 2000 or self.year > 2100:
            raise ValueError("Year must be between 2000 and 2100")

    def to_key(self) -> str:
        """Return normalized period key in YYYY-MM format."""
        return f"{self.year:04d}-{self.month:02d}"
