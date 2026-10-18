from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class Payment(TimeStampedModel):
    """One attempt to pay a booking, successful or not (D11).

    Card data is limited to the brand and the last four digits.
    """

    class Status(models.TextChoices):
        PROCESSING = "processing", _("Processing")
        SUCCEEDED = "succeeded", _("Succeeded")
        FAILED = "failed", _("Failed")

    booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.PROTECT,
        related_name="payments",
        verbose_name=_("booking"),
    )
    idempotency_key = models.UUIDField(
        _("idempotency key"),
        unique=True,
        editable=False,
        help_text=_("Sent with the payment form: the same key never produces a second charge."),
    )
    status = models.CharField(_("status"), max_length=10, choices=Status, default=Status.PROCESSING)
    amount = models.DecimalField(_("amount"), max_digits=10, decimal_places=2)
    currency = models.CharField(_("currency"), max_length=3, default=settings.CURRENCY)
    card_brand = models.CharField(_("card brand"), max_length=20)
    card_last4 = models.CharField(_("last 4 digits"), max_length=4)
    gateway_reference = models.CharField(_("gateway reference"), max_length=64, blank=True)
    decline_code = models.CharField(_("decline code"), max_length=40, blank=True)

    class Meta:
        verbose_name = _("payment")
        verbose_name_plural = _("payments")
        ordering = ["-created_at"]
        constraints = [
            # Last line of defence against a double charge (D11).
            models.UniqueConstraint(
                fields=["booking"],
                condition=Q(status="succeeded"),
                name="payments_payment_one_success_per_booking",
            ),
            models.CheckConstraint(
                condition=Q(amount__gte=Decimal("0")), name="payments_payment_amount_not_negative"
            ),
        ]

    def __str__(self):
        card = f"{self.card_brand} {self.card_last4}"
        return f"{self.booking.reference} · {self.get_status_display()} · {card}"
