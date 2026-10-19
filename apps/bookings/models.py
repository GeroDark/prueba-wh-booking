import builtins
import secrets
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from apps.core.models import TimeStampedModel

from .querysets import BookingQuerySet

# No 0/O or 1/I/L: references are read aloud and typed by guests.
REFERENCE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def generate_reference():
    """Random, non-sequential booking code such as WH-7K3M9QX2 (does not reveal volumes)."""
    return "WH-" + "".join(secrets.choice(REFERENCE_ALPHABET) for _ in range(8))


class Booking(TimeStampedModel):
    """A stay at a property. Starts as a timed hold (PENDING) and becomes CONFIRMED when paid."""

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending payment")
        CONFIRMED = "confirmed", _("Confirmed")
        EXPIRED = "expired", _("Expired")
        CANCELLED = "cancelled", _("Cancelled")

    reference = models.CharField(
        _("reference"), max_length=12, unique=True, default=generate_reference, editable=False
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.PROTECT,
        related_name="bookings",
        verbose_name=_("property"),
    )
    guest = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="bookings",
        verbose_name=_("guest"),
        help_text=_("Empty while an anonymous visitor holds the dates during checkout."),
    )
    status = models.CharField(
        _("status"), max_length=10, choices=Status, default=Status.PENDING, db_index=True
    )
    check_in = models.DateField(_("check-in"))
    check_out = models.DateField(_("check-out"))
    guests = models.PositiveSmallIntegerField(_("guests"))
    expires_at = models.DateTimeField(
        _("hold expires at"),
        null=True,
        blank=True,
        help_text=_("Pending bookings stop blocking their dates after this moment."),
    )
    currency = models.CharField(_("currency"), max_length=3, default=settings.CURRENCY)
    total = models.DecimalField(
        _("total"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0"),
        help_text=_("Snapshot at booking time: later price changes do not affect it."),
    )
    language = models.CharField(
        _("language"), max_length=7, choices=settings.LANGUAGES, default=settings.LANGUAGE_CODE
    )
    confirmed_at = models.DateTimeField(_("confirmed at"), null=True, blank=True)
    # Confirmation e-mail (D37): pending (both empty) -> sending (claimed) -> sent.
    confirmation_claimed_at = models.DateTimeField(
        _("confirmation e-mail being sent since"),
        null=True,
        blank=True,
        help_text=_(
            "Set while a process sends the e-mail. If it stays set for long, that process died "
            "and the retry command takes it over."
        ),
    )
    confirmation_sent_at = models.DateTimeField(
        _("confirmation e-mail sent at"),
        null=True,
        blank=True,
        help_text=_(
            "Set only after the e-mail provider accepted the message. Empty: not sent yet "
            "(it is retried with a command)."
        ),
    )

    objects = BookingQuerySet.as_manager()

    class Meta:
        verbose_name = _("booking")
        verbose_name_plural = _("bookings")
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["property", "check_in", "check_out"])]
        constraints = [
            models.CheckConstraint(
                condition=Q(check_out__gt=F("check_in")),
                name="bookings_booking_check_out_after_check_in",
                violation_error_message=_("Check-out must be after check-in."),
            ),
            models.CheckConstraint(
                condition=Q(guests__gte=1), name="bookings_booking_at_least_one_guest"
            ),
        ]

    def __str__(self):
        return f"{self.reference} · {self.property} ({self.check_in} → {self.check_out})"

    def clean(self):
        """Bookings created or edited in the admin: capacity and overlaps, with a clear message
        instead of the database error (the exclusion constraint still guards everything)."""
        super().clean()
        if not (self.property_id and self.check_in and self.check_out and self.guests):
            return
        errors = {}
        if self.guests > self.property.max_guests:
            errors["guests"] = ngettext(
                "This property hosts up to %(count)d guest.",
                "This property hosts up to %(count)d guests.",
                self.property.max_guests,
            ) % {"count": self.property.max_guests}
        is_blocking = self.status == self.Status.CONFIRMED or (
            self.status == self.Status.PENDING and self.is_hold_active()
        )
        if is_blocking and self.check_out > self.check_in:
            clash = (
                Booking.objects.filter(property=self.property)
                .blocking()
                .overlapping(self.check_in, self.check_out)
                .exclude(pk=self.pk)
                .first()
            )
            if clash:
                errors["check_in"] = _(
                    "These dates overlap booking %(reference)s (%(check_in)s – %(check_out)s)."
                ) % {
                    "reference": clash.reference,
                    "check_in": clash.check_in,
                    "check_out": clash.check_out,
                }
        if errors:
            raise ValidationError(errors)

    # In this class body `property` is the foreign key above: use the builtin decorator explicitly.
    @builtins.property
    def nights(self):
        return (self.check_out - self.check_in).days

    def is_hold_active(self, now=None):
        """A pending booking whose hold has not expired yet."""
        now = now or timezone.now()
        return (
            self.status == self.Status.PENDING
            and self.expires_at is not None
            and self.expires_at > now
        )


class BookingLine(models.Model):
    """One line of the price breakdown, frozen when the dates are held (see D10)."""

    class Kind(models.TextChoices):
        LODGING = "lodging", _("Nights")
        CLEANING = "cleaning", _("Cleaning")
        TAX = "tax", _("Tax")

    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name="lines", verbose_name=_("booking")
    )
    kind = models.CharField(_("type"), max_length=10, choices=Kind)
    label = models.CharField(_("label"), max_length=120)
    amount = models.DecimalField(_("amount"), max_digits=10, decimal_places=2)
    order = models.PositiveSmallIntegerField(_("order"), default=0)

    class Meta:
        verbose_name = _("price line")
        verbose_name_plural = _("price lines")
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.label}: {self.amount}"
