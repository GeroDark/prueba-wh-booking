import re
import uuid
from datetime import date

from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.forms import FriendlyErrorsMixin

from .cards import BRANDS, Card, clean_number, detect_brand, luhn_valid

EXPIRY = re.compile(r"(?P<month>\d{1,2})\s*/\s*(?P<year>\d{2}|\d{4})")
MAX_YEARS_AHEAD = 20


class NoValueTextInput(forms.TextInput):
    """Never writes the submitted value back into the page (used for the security code)."""

    def format_value(self, value):
        return None


class CardForm(FriendlyErrorsMixin, forms.Form):
    """Card details of the payment step (Figma "Información de pago").

    The idempotency key travels in the form: sending the same form twice (double click, reload,
    network retry) reaches the server with the same key and never charges twice.
    """

    card_number = forms.CharField(
        label=_("Card number"),
        max_length=23,
        error_messages={"required": _("Enter the card number.")},
        widget=forms.TextInput(
            attrs={
                "autocomplete": "cc-number",
                "inputmode": "numeric",
                "placeholder": "1234 1234 1234 1234",
                "pattern": r"[0-9 ]{12,23}",
                "data-error-invalid": _("Enter the card number using digits only."),
            }
        ),
    )
    expiry = forms.CharField(
        label=_("Expiry date"),
        max_length=7,
        error_messages={"required": _("Enter the expiry date.")},
        widget=forms.TextInput(
            attrs={
                "autocomplete": "cc-exp",
                "inputmode": "numeric",
                "placeholder": _("MM/YY"),
                "pattern": r"\s*(0?[1-9]|1[0-2])\s*/\s*([0-9]{2}|[0-9]{4})\s*",
                "data-error-invalid": _("Use the format MM/YY, for example 08/29."),
            }
        ),
    )
    cvc = forms.CharField(
        label=_("Security code"),
        max_length=4,
        error_messages={"required": _("Enter the security code.")},
        widget=NoValueTextInput(
            attrs={
                "autocomplete": "cc-csc",
                "inputmode": "numeric",
                "placeholder": "CVC",
                "pattern": r"[0-9]{3,4}",
                "data-error-invalid": _("The security code has 3 or 4 digits."),
            }
        ),
    )
    idempotency_key = forms.UUIDField(widget=forms.HiddenInput, initial=uuid.uuid4)

    def clean_card_number(self):
        number = clean_number(self.cleaned_data["card_number"])
        if not number.isdigit():
            raise forms.ValidationError(
                _("Enter the card number using digits only."), code="card_digits"
            )
        brand = detect_brand(number)
        if brand is None:
            raise forms.ValidationError(
                _("We accept %(brands)s.") % {"brands": ", ".join(brand.name for brand in BRANDS)},
                code="card_brand",
            )
        if len(number) not in brand.lengths or not luhn_valid(number):
            raise forms.ValidationError(
                _("The card number is not valid. Check it and try again."), code="card_invalid"
            )
        return number

    def clean_expiry(self):
        match = EXPIRY.fullmatch(self.cleaned_data["expiry"].strip())
        if not match:
            raise forms.ValidationError(
                _("Use the format MM/YY, for example 08/29."), code="expiry_format"
            )
        month, year = int(match["month"]), int(match["year"])
        year = year + 2000 if year < 100 else year
        if not 1 <= month <= 12:
            raise forms.ValidationError(
                _("Use the format MM/YY, for example 08/29."), code="expiry_format"
            )
        today = timezone.localdate()
        # A card is valid until the last day of its expiry month.
        if (year, month) < (today.year, today.month):
            raise forms.ValidationError(_("This card has expired."), code="expiry_past")
        if date(year, month, 1) > date(today.year + MAX_YEARS_AHEAD, today.month, 1):
            raise forms.ValidationError(
                _("Check the expiry date of the card."), code="expiry_too_far"
            )
        return month, year

    def clean(self):
        cleaned = super().clean()
        number, expiry, cvc = (
            cleaned.get("card_number"),
            cleaned.get("expiry"),
            cleaned.get("cvc", ""),
        )
        if number is None:
            return cleaned
        brand = detect_brand(number)
        if cvc and not (cvc.isdigit() and len(cvc) == brand.cvc_length):
            self.add_error(
                "cvc",
                forms.ValidationError(
                    _("The security code of a %(brand)s card has %(digits)s digits."),
                    code="cvc_length",
                    params={"brand": brand.name, "digits": brand.cvc_length},
                ),
            )
        elif expiry and not self.errors:  # the card exists only for a fully valid form
            cleaned["card"] = Card(number, expiry[0], expiry[1], cvc, brand)
        return cleaned
