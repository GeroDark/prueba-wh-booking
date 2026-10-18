from django.contrib import messages
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import DetailView
from django.views.generic.detail import SingleObjectMixin

from apps.core.templatetags.formatting import money
from apps.properties.models import Property

from .forms import BookingRequestForm
from .models import Booking
from .services import release_hold
from .session import forget_hold, owns_booking


class QuoteView(View):
    """JSON price breakdown for the booking card, recalculated on the server on every change."""

    def get(self, request, slug):
        prop = get_object_or_404(Property.objects.active(), slug=slug)
        form = BookingRequestForm(request.GET, prop=prop)
        if not form.is_valid():
            errors = [str(error) for field_errors in form.errors.values() for error in field_errors]
            return JsonResponse({"ok": False, "errors": errors}, status=400)
        quote = form.quote
        return JsonResponse(
            {
                "ok": True,
                "nights": quote.nights,
                "lines": [
                    {"label": line.label, "amount": money(line.amount)} for line in quote.lines
                ],
                "total": money(quote.total),
            }
        )


class OwnedBookingMixin(SingleObjectMixin):
    """Bookings are looked up by reference and only shown to their owner. Anyone else gets a
    404, so a guessed reference reveals nothing (not even that it exists)."""

    slug_field = "reference"
    slug_url_kwarg = "reference"

    def get_queryset(self):
        return Booking.objects.select_related("property__district__city__country").prefetch_related(
            "lines", "property__images"
        )

    def get_object(self, queryset=None):
        booking = super().get_object(queryset)
        if not owns_booking(self.request, booking):
            raise Http404
        return booking


def property_url_with_dates(booking):
    """Back to the property with the same dates and guests pre-filled."""
    query = urlencode(
        {"check_in": booking.check_in, "check_out": booking.check_out, "guests": booking.guests}
    )
    return f"{reverse('properties:detail', args=[booking.property.slug])}?{query}"


class CheckoutView(OwnedBookingMixin, DetailView):
    """Checkout of a held booking.

    Phase 5: summary and countdown. Phase 7 adds sign-up, payment and the confirmation.
    """

    template_name = "pages/checkout.html"
    context_object_name = "booking"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.object.is_hold_active():
            if self.object.status == Booking.Status.CONFIRMED:
                messages.info(request, _("This booking is already confirmed."))
            else:
                messages.warning(
                    request,
                    _(
                        "Your time to complete the booking ran out and the dates were released. "
                        "Check if they are still available and try again."
                    ),
                )
            return redirect(property_url_with_dates(self.object))
        return self.render_to_response(self.get_context_data(object=self.object))


class ReleaseHoldView(OwnedBookingMixin, View):
    """'Change dates': free the hold now instead of waiting for it to expire."""

    def post(self, request, *args, **kwargs):
        booking = self.get_object()
        release_hold(booking)
        forget_hold(request, booking.reference)
        return redirect(property_url_with_dates(booking))
