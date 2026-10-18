from datetime import date

import pytest
from django.utils import translation

from apps.accounts.phones import InvalidPhone, Phone, parse_phone, region_for_prefix
from apps.accounts.validators import age_on, years_ago


@pytest.mark.parametrize(
    ("raw", "region", "phone"),
    [
        ("987 654 321", "PE", Phone("+51", "987654321")),
        ("(01) 234-5678", "PE", Phone("+51", "12345678")),  # Lima landline
        ("612-345-678", "ES", Phone("+34", "612345678")),
        ("+57 300 123 4567", "PE", Phone("+57", "3001234567")),  # its own prefix wins
    ],
)
def test_parse_phone_accepts_real_numbers(raw, region, phone):
    assert parse_phone(raw, region) == phone


@pytest.mark.parametrize(
    "raw", ["98765432a", "1-800-FLOWERS", "+", "987", "000000000", "+999 123456789"]
)
def test_parse_phone_rejects_impossible_numbers(raw):
    with pytest.raises(InvalidPhone):
        parse_phone(raw, "PE")


@pytest.mark.parametrize(
    ("prefix", "region"), [("+51", "PE"), ("+1", "US"), ("+999", ""), ("abc", "")]
)
def test_region_for_prefix(prefix, region):
    assert region_for_prefix(prefix) == region


def test_years_ago_and_age_handle_29_february():
    assert years_ago(date(2028, 2, 29), 18) == date(2010, 2, 28)
    assert age_on(date(2008, 2, 29), date(2026, 2, 28)) == 17
    assert age_on(date(2008, 2, 29), date(2026, 3, 1)) == 18


@pytest.mark.parametrize(
    "raw", ["+51 51 987654321", "+51 +51 987654321", "0051 51 987654321", "+34 34 612 345 678"]
)
def test_a_country_code_typed_twice_gets_its_own_message(raw):
    with translation.override("en"), pytest.raises(InvalidPhone) as error:
        parse_phone(raw, "PE")

    with translation.override("en"):
        assert "repeated" in str(error.value.message)


@pytest.mark.parametrize("raw", ["+7 701 234 5678", "+1 212 555 0123", "+44 20 7946 0958"])
def test_valid_numbers_starting_like_their_code_are_not_flagged(raw):
    parse_phone(raw, "PE")
