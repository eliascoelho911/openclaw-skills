from compras_divididas.application.services.message_classifier import (
    extract_amount_cents,
    normalize_description,
)


def test_extract_amount_cents_supports_common_brl_formats() -> None:
    assert extract_amount_cents("Mercado R$20") == 2000
    assert extract_amount_cents("Farmacia R$ 20,50") == 2050
    assert extract_amount_cents("Padaria 20.5") == 2050


def test_extract_amount_cents_returns_none_when_amount_missing() -> None:
    assert extract_amount_cents("Bom dia amor") is None


def test_normalize_description_removes_amount_token() -> None:
    assert normalize_description("Mercado R$20") == "Mercado"
    assert normalize_description("Farmacia 20,50") == "Farmacia"
