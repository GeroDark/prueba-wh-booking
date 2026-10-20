from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.http import Http404, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.http import urlencode
from django.utils.module_loading import import_string
from django.utils.translation import get_language
from django.utils.translation import gettext as _
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic import DetailView, FormView, TemplateView
from django.views.generic.detail import SingleObjectMixin

from apps.accounts.forms import CheckoutSignUpForm, GuestDetailsForm
from apps.core.templatetags.formatting import money
from apps.payments.forms import CardForm
from apps.payments.gateways import SimulatedGateway
from apps.payments.models import Payment
from apps.payments.services import HoldExpired, KeyReused, decline_message, pay_booking
from apps.properties.models import Property

from .forms import BookingRequestForm
from .models import Booking
from .services import assign_guest, release_hold
from .session import forget_hold, owns_booking

User = get_user_model()


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


CHECKOUT_FORMS = {
    "signup": CheckoutSignUpForm,
    "details": GuestDetailsForm,
    "payment": CardForm,
}


@method_decorator(
    # Never cached (it shows personal data) and, if an error is reported, Django hides these
    # fields in the report.
    [never_cache, sensitive_post_parameters("password", "card_number", "expiry", "cvc")],
    name="dispatch",
)
class CheckoutView(OwnedBookingMixin, FormView):
    """Checkout of a held booking: two steps on one URL, each POST redirects back (D12).

    1. "signup": a new visitor creates the account with their personal details, or
       "details": a signed-in guest completes the details missing from their profile.
    2. "payment": the card. Paid -> confirmation page; declined -> the reason and a new form.
    """

    template_name = "pages/checkout.html"

    def dispatch(self, request, *args, **kwargs):
        self.object = self.booking = self.get_object()
        if self.booking.status == Booking.Status.CONFIRMED:
            return redirect("bookings:confirmation", self.booking.reference)
        if not self.booking.is_hold_active():
            return self.hold_expired()
        if request.user.is_authenticated:
            assign_guest(self.booking, request.user)
        self.step = self.get_step()
        return super().dispatch(request, *args, **kwargs)

    def get_step(self):
        user = self.request.user
        if not user.is_authenticated:
            return "signup"
        return "payment" if user.has_guest_details else "details"

    def hold_expired(self):
        messages.warning(
            self.request,
            _(
                "Your time to complete the booking ran out and the dates were released. "
                "Check if they are still available and try again."
            ),
        )
        return redirect(property_url_with_dates(self.booking))

    def get_form_class(self):
        return CHECKOUT_FORMS[self.step]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.step == "details":
            kwargs["instance"] = self.request.user
        return kwargs

    def form_valid(self, form):
        return getattr(self, f"{self.step}_valid")(form)

    def signup_valid(self, form):
        form.instance.preferred_language = get_language()
        user = form.save()
        # Logging in keeps the session data, so the hold stays with this visitor (D34).
        login(self.request, user, backend="django.contrib.auth.backends.ModelBackend")
        assign_guest(self.booking, user)
        return redirect(self.request.path)

    def details_valid(self, form):
        form.save()
        return redirect(self.request.path)

    def payment_valid(self, form):
        try:
            payment = pay_booking(
                booking=self.booking,
                card=form.cleaned_data["card"],
                idempotency_key=form.cleaned_data["idempotency_key"],
                language=get_language(),
            )
        except HoldExpired:
            return self.hold_expired()
        except KeyReused:
            return HttpResponseBadRequest()
        if payment.status == Payment.Status.SUCCEEDED:
            # Future messages to this guest in the language they just booked in.
            User.objects.filter(pk=self.request.user.pk).update(preferred_language=get_language())
            return redirect("bookings:confirmation", self.booking.reference)
        # Declined: the reason and a fresh form (new key, card fields empty) to try again.
        context = self.get_context_data(form=CardForm(), payment_error=decline_message(payment))
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        gateway = import_string(settings.PAYMENT_GATEWAY)
        context.update(
            booking=self.booking,
            step=self.step,
            test_cards=gateway.test_cards() if issubclass(gateway, SimulatedGateway) else None,
        )
        return context


@method_decorator(never_cache, name="dispatch")
class BookingConfirmationView(OwnedBookingMixin, DetailView):
    """After paying (Figma "Confirmación"). Only the guest sees it, with the exact address."""

    template_name = "pages/booking_confirmation.html"
    context_object_name = "booking"

    def dispatch(self, request, *args, **kwargs):
        # The link in the e-mail is often opened on another device: without a session the guest
        # signs in and comes back here. Asked for any reference, so it reveals nothing; a
        # different account still gets a 404.
        if not request.user.is_authenticated:
            messages.info(
                request, _("Sign in with the account you booked with to see your booking.")
            )
            return redirect_to_login(request.get_full_path())
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.status != Booking.Status.CONFIRMED:
            return redirect("bookings:checkout", self.object.reference)
        return self.render_to_response(self.get_context_data(object=self.object))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["payment"] = self.object.payments.filter(status=Payment.Status.SUCCEEDED).first()
        return context


@method_decorator(never_cache, name="dispatch")
class MyBookingsView(LoginRequiredMixin, TemplateView):
    """The signed-in guest's bookings (D44): holds still waiting for payment, upcoming stays (one
    in progress included) and past ones. "Past" is decided with the city's local date, as
    everywhere else (D09). Expired and cancelled holds are left out.

    Never cached, like the confirmation: on a shared computer, the browser's Back button after
    signing out must not show someone else's bookings."""

    template_name = "pages/my_bookings.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        bookings = (
            Booking.objects.blocking()  # confirmed + holds that have not expired
            .filter(guest=self.request.user)
            .select_related("property__district__city__country")
            .prefetch_related("property__images")
            .order_by("check_in", "created_at")
        )
        pending, upcoming, past = [], [], []
        for booking in bookings:
            if booking.status == Booking.Status.PENDING:
                pending.append(booking)
            elif booking.check_out > booking.property.city.local_today():
                upcoming.append(booking)
            else:
                past.append(booking)
        past.reverse()  # most recent first
        context.update(pending=pending, upcoming=upcoming, past=past)
        return context


class ReleaseHoldView(OwnedBookingMixin, View):
    """'Change dates': free the hold now instead of waiting for it to expire."""

    def post(self, request, *args, **kwargs):
        booking = self.get_object()
        release_hold(booking)
        forget_hold(request, booking.reference)
        return redirect(property_url_with_dates(booking))
