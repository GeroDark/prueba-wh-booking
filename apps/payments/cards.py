"""Card checks done before talking to the gateway.

The card exists only in memory during the request: the database keeps the brand and the last
four digits, never the number, the expiry or the security code (D11).
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Brand:
    code: str
    name: str
    lengths: tuple[int, ...]
    cvc_length: int


VISA = Brand("visa", "Visa", (13, 16, 19), 3)
MASTERCARD = Brand("mastercard", "Mastercard", (16,), 3)
AMEX = Brand("amex", "American Express", (15,), 4)
BRANDS = (VISA, MASTERCARD, AMEX)

SEPARATORS = re.compile(r"[\s-]")


@dataclass(frozen=True)
class Card:
    number: str
    exp_month: int
    exp_year: int
    cvc: str
    brand: Brand

    @property
    def last4(self):
        return self.number[-4:]

    def __repr__(self):
        # Never print the number or the code, not even in a traceback or a log.
        return f"Card({self.brand.name} •••• {self.last4})"


def clean_number(value):
    """'4242 4242-4242 4242' -> '4242424242424242'."""
    return SEPARATORS.sub("", value)


def luhn_valid(number):
    """Check digit used by every card network: catches typos such as a changed digit or two
    swapped neighbours before the gateway is called."""
    total = 0
    for position, char in enumerate(reversed(number)):
        digit = int(char)
        if position % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def detect_brand(number):
    """Brand from the first digits (IIN ranges). None if it is not one we accept."""
    if number[:2] in ("34", "37"):
        return AMEX
    if number.startswith("4"):
        return VISA
    if len(number) >= 2 and 51 <= int(number[:2]) <= 55:
        return MASTERCARD
    if len(number) >= 6 and 222100 <= int(number[:6]) <= 272099:
        return MASTERCARD
    return None
