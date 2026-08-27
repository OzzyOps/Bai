"""Money is the easiest thing in a global product to get quietly wrong."""
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from bai_platform.money import CurrencyMismatchError, FxRate, Money


class TestExponents:
    def test_zero_decimal_currency(self) -> None:
        assert Money.from_decimal("1250", "JPY").minor == 1250

    def test_three_decimal_currency(self) -> None:
        assert Money.from_decimal("12.345", "KWD").minor == 12345

    def test_two_decimal_default(self) -> None:
        assert Money.from_decimal("12.50", "GBP").minor == 1250

    @pytest.mark.parametrize(("amount", "expected"), [("0.005", 0), ("0.015", 2), ("0.025", 2)])
    def test_bankers_rounding(self, amount: str, expected: int) -> None:
        assert Money.from_decimal(amount, "USD").minor == expected


class TestTypeSafety:
    def test_float_rejected(self) -> None:
        with pytest.raises(TypeError):
            Money(12.5, "USD")  # type: ignore[arg-type]

    def test_bool_rejected(self) -> None:
        with pytest.raises(TypeError):
            Money(True, "USD")  # type: ignore[arg-type]

    def test_invalid_currency_code(self) -> None:
        with pytest.raises(ValueError):
            Money(100, "EURO")

    def test_currency_normalised(self) -> None:
        assert Money(100, "usd").currency == "USD"


class TestArithmetic:
    def test_cross_currency_addition_raises(self) -> None:
        with pytest.raises(CurrencyMismatchError):
            Money(100, "GBP") + Money(100, "JPY")

    def test_allocation_loses_nothing(self) -> None:
        parts = Money(1000, "USD").allocate([1, 1, 1])
        assert sum(p.minor for p in parts) == 1000
        assert [p.minor for p in parts] == [334, 333, 333]

    def test_allocation_by_ratio(self) -> None:
        assert [p.minor for p in Money(1000, "JPY").allocate([70, 30])] == [700, 300]

    def test_allocation_rejects_zero_total(self) -> None:
        with pytest.raises(ValueError):
            Money(100, "USD").allocate([0, 0])


class TestFx:
    def test_conversion_is_explicit_and_dated(self) -> None:
        rate = FxRate("GBP", "JPY", Decimal("189.4"), datetime.now(UTC), "ECB")
        assert rate.convert(Money(1250, "GBP")).minor == 2368

    def test_wrong_base_raises(self) -> None:
        rate = FxRate("GBP", "JPY", Decimal("189.4"), datetime.now(UTC), "ECB")
        with pytest.raises(CurrencyMismatchError):
            rate.convert(Money(1250, "USD"))
