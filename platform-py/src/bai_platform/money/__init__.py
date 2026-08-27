"""Money handling for BAi. Multi-currency by construction.

Rules enforced here, not by convention:
  * money is integer minor units, never a float
  * currency exponent comes from ISO 4217, never assumed to be 2
  * arithmetic across currencies raises; conversion is explicit and rated
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_EVEN, Decimal

__all__ = ["EXPONENTS", "Currency", "CurrencyMismatchError", "FxRate", "Money"]


class CurrencyMismatchError(ValueError):
    """Raised when arithmetic is attempted across differing currencies."""


# ISO 4217 minor-unit exponents. Anything absent defaults to 2, but the
# zero- and three-decimal currencies below are the ones that break naive code.
EXPONENTS: dict[str, int] = {
    "JPY": 0, "KRW": 0, "VND": 0, "CLP": 0, "ISK": 0, "PYG": 0, "RWF": 0,
    "UGX": 0, "VUV": 0, "XAF": 0, "XOF": 0, "XPF": 0, "DJF": 0, "GNF": 0, "KMF": 0,
    "BHD": 3, "IQD": 3, "JOD": 3, "KWD": 3, "LYD": 3, "OMR": 3, "TND": 3,
}

Currency = str  # ISO 4217 alpha-3


def exponent_for(currency: Currency) -> int:
    return EXPONENTS.get(currency.upper(), 2)


@dataclass(frozen=True, slots=True)
class Money:
    """An exact monetary amount.

    ``minor`` is the amount in the currency's smallest unit: 1250 GBP-minor is
    £12.50; 1250 JPY-minor is ¥1250, because JPY has no minor unit.
    """

    minor: int
    currency: Currency

    def __post_init__(self) -> None:
        if not isinstance(self.minor, int) or isinstance(self.minor, bool):
            raise TypeError("Money.minor must be int — never float, never Decimal")
        if len(self.currency) != 3 or not self.currency.isalpha():
            raise ValueError(f"currency must be ISO 4217 alpha-3, got {self.currency!r}")
        object.__setattr__(self, "currency", self.currency.upper())

    # ── construction ────────────────────────────────────────────────────────
    @classmethod
    def from_decimal(cls, amount: Decimal | str | int, currency: Currency) -> Money:
        """Build from a major-unit amount. Half-even rounding, banker's rules."""
        exp = exponent_for(currency)
        quantum = Decimal(1).scaleb(-exp)
        value = Decimal(str(amount)).quantize(quantum, rounding=ROUND_HALF_EVEN)
        return cls(int(value.scaleb(exp)), currency)

    @classmethod
    def zero(cls, currency: Currency) -> Money:
        return cls(0, currency)

    # ── access ──────────────────────────────────────────────────────────────
    @property
    def exponent(self) -> int:
        return exponent_for(self.currency)

    def to_decimal(self) -> Decimal:
        return Decimal(self.minor).scaleb(-self.exponent)

    # ── arithmetic ──────────────────────────────────────────────────────────
    def _check(self, other: Money) -> None:
        if self.currency != other.currency:
            raise CurrencyMismatchError(
                f"cannot combine {self.currency} and {other.currency}; convert explicitly"
            )

    def __add__(self, other: Money) -> Money:
        self._check(other)
        return Money(self.minor + other.minor, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._check(other)
        return Money(self.minor - other.minor, self.currency)

    def __mul__(self, factor: int | Decimal | str) -> Money:
        product = Decimal(self.minor) * Decimal(str(factor))
        return Money(int(product.quantize(Decimal(1), rounding=ROUND_HALF_EVEN)), self.currency)

    def __neg__(self) -> Money:
        return Money(-self.minor, self.currency)

    def allocate(self, ratios: list[int]) -> list[Money]:
        """Split without losing a unit. Remainder distributed largest-ratio-first."""
        if not ratios or any(r < 0 for r in ratios):
            raise ValueError("ratios must be non-empty and non-negative")
        total = sum(ratios)
        if total == 0:
            raise ValueError("ratios must not sum to zero")
        shares = [self.minor * r // total for r in ratios]
        remainder = self.minor - sum(shares)
        order = sorted(range(len(ratios)), key=lambda i: ratios[i], reverse=True)
        for i in range(remainder):
            shares[order[i % len(order)]] += 1
        return [Money(s, self.currency) for s in shares]

    # ── presentation ────────────────────────────────────────────────────────
    def format(self, locale: str = "en-US") -> str:
        """Human-readable. Real locale formatting belongs on the client via Intl;
        this is a server-side fallback for exports and email."""
        return f"{self.to_decimal():,.{self.exponent}f} {self.currency}"

    def __str__(self) -> str:
        return self.format()


@dataclass(frozen=True, slots=True)
class FxRate:
    """A pinned, dated conversion rate. Never look one up implicitly."""

    base: Currency
    quote: Currency
    rate: Decimal
    as_of: datetime
    source: str

    def convert(self, amount: Money) -> Money:
        if amount.currency != self.base.upper():
            raise CurrencyMismatchError(
                f"rate converts {self.base}, not {amount.currency}"
            )
        return Money.from_decimal(amount.to_decimal() * self.rate, self.quote)
