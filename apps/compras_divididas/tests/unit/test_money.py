from decimal import Decimal

from compras_divididas.domain.money import format_money, parse_money, quantize_money


def test_quantize_money_uses_round_half_up() -> None:
    assert quantize_money(Decimal("10.005")) == Decimal("10.01")
    assert quantize_money(Decimal("10.004")) == Decimal("10.00")


def test_parse_money_returns_quantized_decimal() -> None:
    assert parse_money("2.675") == Decimal("2.68")


def test_format_money_has_two_decimal_places() -> None:
    assert format_money(Decimal("5")) == "5.00"
