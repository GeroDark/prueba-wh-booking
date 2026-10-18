"""Phone numbers with Google's libphonenumber (the `phonenumbers` package, D36).

Each country has its own lengths and prefixes (a Peruvian mobile has 9 digits and starts with
9; a Spanish one, 9 digits starting with 6 or 7), so a regular expression cannot validate them.
"""

import re
from dataclasses import dataclass

import phonenumbers
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django_countries import countries

# Only what people type in a phone number. libphonenumber would turn letters into digits
# ("1-800-FLOWERS"), which is not what a guest means.
TYPED_PHONE = re.compile(r"[\d\s().+\-]{4,25}")


class InvalidPhone(ValueError):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class Phone:
    prefix: str  # "+51"
    number: str  # "987654321"


def region_choices():
    """[("PE", "Perú (+51)"), ...]: Wynwood House countries first (COUNTRIES_FIRST), then
    the rest in the visitor's language."""
    choices = []
    for index, country in enumerate(countries):
        if index == len(settings.COUNTRIES_FIRST):
            choices.append(("", settings.COUNTRIES_FIRST_BREAK))
        code = phonenumbers.country_code_for_region(country.code)
        if code:
            choices.append((country.code, f"{country.name} (+{code})"))
    return choices


def region_for_prefix(prefix):
    """'+51' -> 'PE' (the main country of a shared code such as +1 is the United States)."""
    digits = prefix.lstrip("+")
    if not digits.isdigit():
        return ""
    region = phonenumbers.region_code_for_country_code(int(digits))
    return "" if region == phonenumbers.UNKNOWN_REGION else region


def parse_phone(raw, region):
    """Validate a number typed for `region` (or with its own +prefix) and split it."""
    raw = raw.strip()
    if not TYPED_PHONE.fullmatch(raw):
        raise InvalidPhone(_("Use only digits, spaces or dashes."))
    try:
        number = phonenumbers.parse(raw, region or None)
    except phonenumbers.NumberParseException:
        raise InvalidPhone(_("Enter a valid phone number.")) from None
    if not phonenumbers.is_valid_number(number):
        raise InvalidPhone(_("Enter a valid phone number for the selected country."))
    return Phone(
        prefix=f"+{number.country_code}",
        number=phonenumbers.national_significant_number(number),
    )
