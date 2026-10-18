from decimal import Decimal

from django import template
from django.conf import settings
from django.utils.formats import number_format

register = template.Library()

CURRENCY_SYMBOLS = {"USD": "US$", "EUR": "€", "PEN": "S/", "COP": "COL$", "MXN": "MX$"}


@register.filter
def money(value, currency=None):
    """US$ 1.250 (es) / US$ 1,250 (en). Cents are only shown when there are any: US$ 83,50."""
    if value in (None, ""):
        return ""
    amount = Decimal(value)
    decimals = 0 if amount == amount.to_integral_value() else 2
    symbol = CURRENCY_SYMBOLS.get(currency or settings.CURRENCY, currency or settings.CURRENCY)
    formatted = number_format(amount, decimal_pos=decimals, use_l10n=True, force_grouping=True)
    return f"{symbol} {formatted}"
