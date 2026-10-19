from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.translation import ngettext
from django.views.generic import DetailView, ListView
from django.views.generic.edit import FormMixin

from apps.bookings.forms import BookingRequestForm
from apps.bookings.models import Booking
from apps.bookings.services import hold_dates
from apps.bookings.session import remember_hold, session_holds
from apps.core.templatetags.formatting import money

from .forms import SearchForm
from .models import Property


def map_marker(prop):
    """Data for one map pin. Coordinates are the public, rounded ones (see D27)."""
    lat, lng = prop.public_coordinates
    cover = prop.cover_image
    return {
        "id": prop.pk,
        "title": prop.title,
        "lat": lat,
        "lng": lng,
        "price": money(prop.price_per_night),
        "location": f"{prop.district.name}, {prop.city.name}",
        "url": reverse("properties:detail", args=[prop.slug]),
        "image": cover.image.url if cover else "",
    }


class PropertySearchView(ListView):
    """Search results: filters from the search bar, a paginated list and a map of the same page."""

    template_name = "pages/search_results.html"
    context_object_name = "properties"
    paginate_by = 10

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.form = SearchForm(request.GET or None)
        self.filters = self.get_filters()

    def get_filters(self):
        """Valid filters only: an invalid field shows its error but does not block the others."""
        if not self.form.is_bound:
            return {}
        self.form.is_valid()
        return {name: value for name, value in self.form.cleaned_data.items() if value}

    def get_queryset(self):
        return Property.objects.active().search(**self.filters).with_card_data()

    def paginate_queryset(self, queryset, page_size):
        """`?page=abc` opens the first page and `?page=999` the last one, instead of a 404
        (shared or old links keep working when there are fewer results)."""
        paginator = self.get_paginator(queryset, page_size)
        page = paginator.get_page(self.request.GET.get(self.page_kwarg))
        return paginator, page, page.object_list, page.has_other_pages()

    def get_summary(self):
        """Readable active filters, e.g. ["Lima", "10 nov – 14 nov 2026", "2 huéspedes"]."""
        filters = self.filters
        parts = []
        place = filters.get("district") or filters.get("city") or filters.get("country")
        if filters.get("district"):
            parts.append(f"{filters['district'].name}, {filters['district'].city.name}")
        elif place:
            parts.append(place.name)
        if filters.get("check_in") and filters.get("check_out"):
            arrival = date_format(filters["check_in"], "j M")
            departure = date_format(filters["check_out"], "j M Y")
            parts.append(f"{arrival} – {departure}")
        if filters.get("guests"):
            guests = filters["guests"]
            parts.append(
                ngettext("%(count)d guest", "%(count)d guests", guests) % {"count": guests}
            )
        return parts

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            search_form=self.form,
            filters=self.filters,
            summary=self.get_summary(),
            map_markers=[
                map_marker(prop) for prop in context["properties"] if prop.public_coordinates
            ],
        )
        return context


class PropertyDetailView(FormMixin, DetailView):
    """Property page with the booking card.

    GET shows the property; POST ("Book now") holds the dates and sends the visitor to the
    checkout. This is Django's documented FormMixin + DetailView pattern: on errors the same
    page is rendered again with the messages next to the fields.
    """

    template_name = "pages/property_detail.html"
    context_object_name = "property"
    form_class = BookingRequestForm

    def get_queryset(self):
        return Property.objects.active().with_card_data().prefetch_related("amenities")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["prop"] = self.object
        # Dates coming from the search (or from an expired checkout) arrive in the URL:
        # bind them so the page shows availability and the price right away.
        if self.request.method == "GET" and {"check_in", "check_out"} <= self.request.GET.keys():
            kwargs["data"] = {
                "check_in": self.request.GET["check_in"],
                "check_out": self.request.GET["check_out"],
                "guests": self.request.GET.get("guests") or 1,
            }
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        prop = self.object
        today = prop.district.city.local_today()
        taken = (
            Booking.objects.filter(property=prop, check_out__gt=today)
            .blocking()
            .order_by("check_in")
        )
        context.update(
            # Nights that are taken: from check-in to the day before check-out.
            unavailable_dates=[
                {
                    "from": booking.check_in.isoformat(),
                    "to": (booking.check_out - timedelta(days=1)).isoformat(),
                }
                for booking in taken
            ],
            calendar={
                "min_date": today.isoformat(),
                "max_date": (today + timedelta(days=settings.BOOKING_MAX_DAYS_AHEAD)).isoformat(),
                "max_nights": settings.BOOKING_MAX_NIGHTS,
            },
            location=prop.public_coordinates,
            hold_minutes=settings.BOOKING_HOLD_MINUTES,
        )
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if not form.is_valid():
            return self.form_invalid(form)
        try:
            booking = hold_dates(
                prop=self.object,
                check_in=form.cleaned_data["check_in"],
                check_out=form.cleaned_data["check_out"],
                guests=form.cleaned_data["guests"],
                guest=request.user if request.user.is_authenticated else None,
                released_holds=session_holds(request),
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        remember_hold(request, booking.reference)
        return redirect("bookings:checkout", reference=booking.reference)
