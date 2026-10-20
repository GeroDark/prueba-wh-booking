from itertools import groupby

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.bookings.services import date_errors
from apps.core.forms import FriendlyErrorsMixin

from .models import City, Country, District, earliest_local_today

MAX_SEARCH_GUESTS = 16


class GroupedModelChoiceIterator(forms.models.ModelChoiceIterator):
    """Render choices as <optgroup>s, one per value of `group_by` (e.g. districts by city)."""

    def __iter__(self):
        if self.field.empty_label is not None:
            yield ("", self.field.empty_label)
        queryset = self.queryset.select_related(self.field.group_by)
        for group, objects in groupby(queryset, key=lambda obj: getattr(obj, self.field.group_by)):
            yield (str(group), [self.choice(obj) for obj in objects])


class GroupedModelChoiceField(forms.ModelChoiceField):
    iterator = GroupedModelChoiceIterator

    def __init__(self, *args, group_by, **kwargs):
        self.group_by = group_by
        super().__init__(*args, **kwargs)


class SearchForm(FriendlyErrorsMixin, forms.Form):
    """Search bar used on the home page, the footer and the results page (GET)."""

    country = forms.ModelChoiceField(
        label=_("Country"),
        queryset=Country.objects.none(),
        required=False,
        to_field_name="slug",
        widget=forms.HiddenInput,
    )
    city = forms.ModelChoiceField(
        label=_("City or destination"),
        queryset=City.objects.none(),
        required=False,
        to_field_name="slug",
        empty_label=_("City or destination"),
    )
    district = GroupedModelChoiceField(
        label=_("District"),
        queryset=District.objects.none(),
        required=False,
        group_by="city",
        empty_label=_("All districts"),
    )
    check_in = forms.DateField(
        label=_("Check-in"), required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    check_out = forms.DateField(
        label=_("Check-out"), required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    guests = forms.IntegerField(
        label=_("Guests"),
        required=False,
        min_value=1,
        max_value=MAX_SEARCH_GUESTS,
        widget=forms.NumberInput(attrs={"placeholder": _("Number of guests")}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != "country":
                field.widget.attrs.setdefault("class", "search-bar__control")
        self.fields["district"].widget.attrs["data-district-select"] = ""
        # Inside its city's <optgroup> the district needs no "…, City" suffix.
        self.fields["district"].label_from_instance = lambda district: district.name
        self.fields["city"].widget.attrs["data-city-select"] = ""
        # Only places that actually have something to book.
        bookable = {"is_active": True, "districts__properties__is_active": True}
        self.fields["country"].queryset = Country.objects.filter(
            is_active=True, cities__districts__properties__is_active=True
        ).distinct()
        self.fields["city"].queryset = (
            City.objects.filter(**bookable).select_related("country").distinct().order_by("name")
        )
        self.fields["district"].queryset = (
            District.objects.filter(city__is_active=True, properties__is_active=True)
            .distinct()
            .order_by("city__name", "name")
        )

    def clean(self):
        cleaned = super().clean()
        city, district = cleaned.get("city"), cleaned.get("district")
        check_in, check_out = cleaned.get("check_in"), cleaned.get("check_out")

        if city and district and district.city_id != city.pk:
            self.add_error("district", _("This district is not in the selected city."))
        if district and not city:
            cleaned["city"] = district.city

        if bool(check_in) != bool(check_out):
            self.add_error(
                "check_out" if check_in else "check_in", _("Choose both arrival and departure.")
            )
        elif check_in and check_out:
            # Same rules as booking (past, 365 days ahead, 1 to 30 nights), so the results never
            # list stays that cannot be booked afterwards. "Today" is the date where the property
            # is (D09): the chosen city's, or without a city the earliest one among the cities
            # (the results then leave out the cities where that arrival is already past).
            place = cleaned.get("city")
            today = place.local_today() if place else earliest_local_today()
            for field, error in date_errors(check_in, check_out, today).items():
                self.add_error(field, error)
        return cleaned

    @property
    def districts_by_city(self):
        """{city_slug: [{"id": .., "name": ..}]} for the dependent district select (JS)."""
        return {
            city.slug: [{"id": d.pk, "name": d.name} for d in districts]
            for city, districts in groupby(
                self.fields["district"].queryset.select_related("city"), key=lambda d: d.city
            )
        }
