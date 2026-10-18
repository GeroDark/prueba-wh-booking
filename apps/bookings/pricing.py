"""Price of a stay, computed only on the server (see D10).

The same function feeds the live quote on the property page, the hold and, later, the payment,
so the amount the guest sees is exactly the amount that gets charged.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.utils import translation
from django.utils.translation import gettext, ngettext

from apps.core.templatetags.formatting import money

from .models import BookingLine

CENT = Decimal("0.01")


def to_cents(amount):
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class QuoteLine:
    kind: str
    labels: dict  # {"es": "...", "en": "..."}: frozen in both languages
    amount: Decimal

    @property
    def label(self):
        return self.labels.get(translation.get_language(), self.labels[settings.LANGUAGE_CODE])


@dataclass(frozen=True)
class Quote:
    nights: int
    lines: tuple
    total: Decimal
    currency: str = settings.CURRENCY


def _in_each_language(build):
    labels = {}
    for code, _name in settings.LANGUAGES:
        with translation.override(code):
            labels[code] = build()
    return labels


def quote_stay(prop, check_in, check_out):
    """Nights × nightly price + cleaning fee + the active taxes of the property's country.

    Taxes apply to lodging + cleaning and are rounded half-up to cents, line by line,
    so the lines always add up to the total shown.
    """
    nights = (check_out - check_in).days
    lodging = to_cents(prop.price_per_night * nights)
    lines = [
        QuoteLine(
            BookingLine.Kind.LODGING,
            _in_each_language(
                lambda: (
                    ngettext("%(price)s × %(count)d night", "%(price)s × %(count)d nights", nights)
                    % {"price": money(prop.price_per_night), "count": nights}
                )
            ),
            lodging,
        )
    ]
    if prop.cleaning_fee:
        lines.append(
            QuoteLine(
                BookingLine.Kind.CLEANING,
                _in_each_language(lambda: gettext("Cleaning fee")),
                to_cents(prop.cleaning_fee),
            )
        )

    taxable = sum((line.amount for line in lines), Decimal("0"))
    for tax in prop.district.city.country.taxes.filter(is_active=True):
        rate = f"{tax.rate.normalize():f}"  # 19.00 -> "19", 3.50 -> "3.5"
        labels = {
            code: f"{getattr(tax, f'name_{code}') or tax.name_es} ({rate}%)"
            for code, _name in settings.LANGUAGES
        }
        lines.append(QuoteLine(BookingLine.Kind.TAX, labels, to_cents(taxable * tax.rate / 100)))

    total = sum((line.amount for line in lines), Decimal("0"))
    return Quote(nights=nights, lines=tuple(lines), total=total)
