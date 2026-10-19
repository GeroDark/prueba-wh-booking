"""Booking rules. Views and forms call these functions; they never touch bookings directly.

Validation happens in layers (see D07):
1. the calendar disables taken and past dates (UX only);
2. `validate_stay` gives clear, translated errors before anything is written;
3. `hold_dates` locks the property row and re-checks availability inside a transaction;
4. PostgreSQL's exclusion constraint rejects overlapping bookings as the last line of defence.
"""

from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import get_language, ngettext
from django.utils.translation import gettext as _

from apps.properties.models import Property

from .models import Booking, BookingLine
from .pricing import quote_stay


def unavailable_error():
    return ValidationError(
        _("These dates are no longer available. Please choose other dates."), code="unavailable"
    )


def date_errors(check_in, check_out, today):
    """Date rules shared by the search and the booking: {field: ValidationError}.

    The search applies them too, so it never shows stays that cannot be booked afterwards.
    """
    errors = {}
    if check_in < today:
        errors["check_in"] = ValidationError(_("Arrival cannot be in the past."), code="past")
    elif check_in > today + timedelta(days=settings.BOOKING_MAX_DAYS_AHEAD):
        errors["check_in"] = ValidationError(
            _("Bookings open up to %(days)d days in advance.")
            % {"days": settings.BOOKING_MAX_DAYS_AHEAD},
            code="too_far",
        )

    nights = (check_out - check_in).days
    if nights < 1:
        errors["check_out"] = ValidationError(_("Departure must be after arrival."), code="order")
    elif nights > settings.BOOKING_MAX_NIGHTS:
        errors["check_out"] = ValidationError(
            ngettext(
                "Online bookings are limited to %(count)d night. "
                "For longer stays, contact us for a monthly rate.",
                "Online bookings are limited to %(count)d nights. "
                "For longer stays, contact us for a monthly rate.",
                settings.BOOKING_MAX_NIGHTS,
            )
            % {"count": settings.BOOKING_MAX_NIGHTS},
            code="too_long",
        )
    return errors


def validate_stay(prop, check_in, check_out, guests):
    """Rules that do not depend on other bookings. Raises ValidationError with field errors."""
    # "Past" depends on where the property is (D09).
    errors = date_errors(check_in, check_out, prop.district.city.local_today())

    if guests < 1:
        errors["guests"] = ValidationError(_("At least one guest is required."), code="guests")
    elif guests > prop.max_guests:
        errors["guests"] = ValidationError(
            ngettext(
                "This property hosts up to %(count)d guest.",
                "This property hosts up to %(count)d guests.",
                prop.max_guests,
            )
            % {"count": prop.max_guests},
            code="capacity",
        )

    if errors:
        raise ValidationError(errors)


def is_available(prop, check_in, check_out, now=None):
    """Read-only availability check, used by the live quote (no locks)."""
    return (
        not Booking.objects.filter(property=prop)
        .blocking(now)
        .overlapping(check_in, check_out)
        .exists()
    )


def hold_dates(*, prop, check_in, check_out, guests, guest=None, released_holds=()):
    """Create a PENDING booking that blocks the dates for BOOKING_HOLD_MINUTES.

    `released_holds` are references of this visitor's previous holds: they are cancelled
    first, so one visitor cannot block several calendars at once (D08).
    Returns the new booking or raises ValidationError.
    """
    validate_stay(prop, check_in, check_out, guests)
    try:
        with transaction.atomic():
            # Lock the property row: concurrent holds for the same property wait here
            # and then see each other's booking (no double booking).
            prop = Property.objects.select_for_update().get(pk=prop.pk, is_active=True)
            now = timezone.now()

            Booking.objects.filter(
                reference__in=released_holds, status=Booking.Status.PENDING
            ).update(status=Booking.Status.CANCELLED)
            # Lazy expiry made explicit before inserting, so the database constraint
            # (which cannot use "now") only sees holds that are really alive.
            Booking.objects.filter(
                property=prop, status=Booking.Status.PENDING, expires_at__lte=now
            ).update(status=Booking.Status.EXPIRED)

            if not is_available(prop, check_in, check_out, now):
                raise unavailable_error()

            quote = quote_stay(prop, check_in, check_out)
            booking = Booking.objects.create(
                property=prop,
                guest=guest,
                status=Booking.Status.PENDING,
                check_in=check_in,
                check_out=check_out,
                guests=guests,
                expires_at=now + timedelta(minutes=settings.BOOKING_HOLD_MINUTES),
                total=quote.total,
                currency=quote.currency,
                language=get_language() or settings.LANGUAGE_CODE,
            )
            BookingLine.objects.bulk_create(
                [
                    BookingLine(
                        booking=booking,
                        kind=line.kind,
                        amount=line.amount,
                        order=order,
                        **{f"label_{code}": text for code, text in line.labels.items()},
                    )
                    for order, line in enumerate(quote.lines)
                ]
            )
    except Property.DoesNotExist as error:  # deactivated while the visitor was on the page
        raise unavailable_error() from error
    except IntegrityError as error:
        # The exclusion constraint caught a race the lock did not (e.g. a write outside
        # this service). Report it as the same, user-friendly availability error.
        raise unavailable_error() from error
    return booking


def assign_guest(booking, user):
    """The visitor signed up or signed in during checkout: the hold becomes their booking.

    Only a hold without a guest can be claimed, so nobody can take over someone else's booking.
    """
    if Booking.objects.filter(pk=booking.pk, guest__isnull=True).update(guest=user):
        booking.guest = user


def release_hold(booking):
    """The visitor gave up: free the dates immediately instead of waiting for the expiry."""
    return Booking.objects.filter(pk=booking.pk, status=Booking.Status.PENDING).update(
        status=Booking.Status.CANCELLED
    )


def expire_holds(now=None):
    """Mark holds past their expiry as EXPIRED. Housekeeping only: availability is already
    correct without it, because expired holds stop blocking on their own."""
    return Booking.objects.filter(
        status=Booking.Status.PENDING, expires_at__lte=now or timezone.now()
    ).update(status=Booking.Status.EXPIRED)
