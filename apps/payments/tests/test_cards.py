from datetime import date

import pytest
import time_machine
from django.utils import translation

from apps.payments.cards import AMEX, MASTERCARD, VISA, Card, detect_brand, luhn_valid
from apps.payments.forms import CardForm


@pytest.fixture(autouse=True)
def english():
    """Messages are compared with the source texts."""
    with translation.override("en"):
        yield


@pytest.mark.parametrize(
    "number", ["4242424242424242", "5555555555554444", "378282246310005", "4000000000000002"]
)
def test_luhn_accepts_valid_numbers(number):
    assert luhn_valid(number)


@pytest.mark.parametrize(
    "number",
    [
        "4242424242424241",  # last digit changed
        "2424424242424242",  # two neighbours swapped
        "1234567812345678",
    ],
)
def test_luhn_catches_typos(number):
    assert not luhn_valid(number)


@pytest.mark.parametrize(
    ("number", "brand"),
    [
        ("4242424242424242", VISA),
        ("5105105105105100", MASTERCARD),
        ("2221000000000009", MASTERCARD),  # 2-series
        ("378282246310005", AMEX),
        ("341111111111111", AMEX),
        ("6011111111111117", None),  # Discover: not accepted
        ("3530111333300000", None),  # JCB
    ],
)
def test_detect_brand(number, brand):
    assert detect_brand(number) == brand


def test_card_never_prints_its_number_or_code():
    card = Card("4242424242424242", 12, 2030, "123", VISA)

    assert repr(card) == "Card(Visa •••• 4242)"
    assert "424242424242" not in repr(card) and "123" not in repr(card)


# Card form

KEY = "6f1c6a3e-6a4f-4b8e-9d9c-0c1a2b3c4d5e"


def card_form(**data):
    values = {
        "card_number": "4242 4242 4242 4242",
        "expiry": "12/30",
        "cvc": "123",
        "idempotency_key": KEY,
    }
    values.update(data)
    return CardForm(values)


@time_machine.travel(date(2026, 10, 18))
@pytest.mark.parametrize(
    ("data", "card_number", "exp"),
    [
        ({}, "4242424242424242", (12, 2030)),
        ({"card_number": "4242-4242-4242-4242"}, "4242424242424242", (12, 2030)),
        ({"expiry": " 1 / 27 "}, "4242424242424242", (1, 2027)),
        ({"expiry": "10/2026"}, "4242424242424242", (10, 2026)),  # valid until the month ends
        ({"card_number": "3782 822463 10005", "cvc": "1234"}, "378282246310005", (12, 2030)),
    ],
)
def test_card_form_accepts(data, card_number, exp):
    form = card_form(**data)

    assert form.is_valid(), form.errors
    card = form.cleaned_data["card"]
    assert card.number == card_number
    assert (card.exp_month, card.exp_year) == exp


@time_machine.travel(date(2026, 10, 18))
@pytest.mark.parametrize(
    ("data", "field", "message"),
    [
        ({"card_number": ""}, "card_number", "Enter the card number."),
        ({"card_number": "4242 4242 4242 424a"}, "card_number", "digits only"),
        ({"card_number": "4242424242424241"}, "card_number", "not valid"),  # Luhn
        ({"card_number": "424242424242"}, "card_number", "not valid"),  # too short for Visa
        ({"card_number": "6011111111111117"}, "card_number", "We accept"),  # Discover
        ({"expiry": "13/30"}, "expiry", "MM/YY"),
        ({"expiry": "00/30"}, "expiry", "MM/YY"),
        ({"expiry": "1230"}, "expiry", "MM/YY"),
        ({"expiry": "09/26"}, "expiry", "expired"),
        ({"expiry": "12/60"}, "expiry", "Check the expiry date"),
        ({"cvc": "12"}, "cvc", "3 digits"),
        ({"cvc": "12a"}, "cvc", "3 digits"),
        ({"card_number": "378282246310005", "cvc": "123"}, "cvc", "4 digits"),  # Amex
        ({"idempotency_key": "not-a-uuid"}, "idempotency_key", "form expired"),
    ],
)
def test_card_form_rejects(data, field, message):
    form = card_form(**data)

    assert not form.is_valid()
    assert message in " ".join(form.errors[field])
    assert "card" not in form.cleaned_data


def test_security_code_is_never_written_back_into_the_page():
    form = card_form(cvc="987", expiry="99/99")
    form.is_valid()

    html = str(form["cvc"])
    assert "987" not in html
