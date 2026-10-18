from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .pricing import quote_stay
from .services import is_available, unavailable_error, validate_stay


class BookingRequestForm(forms.Form):
    """Dates and guests on the property page. Used for the live quote and for "Book now"."""

    check_in = forms.DateField(label=_("Check-in"), widget=forms.DateInput(attrs={"type": "date"}))
    check_out = forms.DateField(
        label=_("Check-out"), widget=forms.DateInput(attrs={"type": "date"})
    )
    guests = forms.IntegerField(label=_("Guests"), min_value=1, initial=1)

    def __init__(self, *args, prop, **kwargs):
        super().__init__(*args, **kwargs)
        self.prop = prop
        self.quote = None
        self.fields["guests"].widget.attrs.update(min=1, max=prop.max_guests)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "booking-form__control")

    def clean(self):
        cleaned = super().clean()
        check_in, check_out = cleaned.get("check_in"), cleaned.get("check_out")
        guests = cleaned.get("guests")
        if not (check_in and check_out and guests):
            return cleaned
        try:
            validate_stay(self.prop, check_in, check_out, guests)
        except ValidationError as error:
            self.add_error(None, error)  # a dict of field errors is spread onto the fields
            return cleaned
        if not is_available(self.prop, check_in, check_out):
            raise unavailable_error()
        self.quote = quote_stay(self.prop, check_in, check_out)
        return cleaned
