import builtins
import secrets

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils.translation import gettext_lazy as _

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
    language = models.CharField(
        _("language"), max_length=7, choices=settings.LANGUAGES, default=settings.LANGUAGE_CODE
    )
    confirmed_at = models.DateTimeField(_("confirmed at"), null=True, blank=True)

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

    # In this class body `property` is the foreign key above: use the builtin decorator explicitly.
    @builtins.property
    def nights(self):
        return (self.check_out - self.check_in).days
