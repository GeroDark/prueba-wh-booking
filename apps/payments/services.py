"""Paying a held booking exactly once (D11).

| Risk                          | Protection here                                                  |
|-------------------------------|------------------------------------------------------------------|
| Same form sent twice          | `idempotency_key`: the second request gets the first payment     |
| Two tabs paying at once       | `select_for_update` on the booking; the second sees it confirmed |
| Hold expired while paying     | Checked under the lock, before calling the gateway               |
| A bug that bypasses all above | DB constraint: one successful payment per booking                |
"""

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.bookings.models import Booking

from .gateways import get_gateway
from .models import Payment

DECLINE_MESSAGES = {
    "card_declined": _("Your card was declined. Try another card."),
    "insufficient_funds": _("The card has insufficient funds. Try another card."),
    "test_card_required": _(
        "This is a demo and no real charges are made: use one of the test cards shown below."
    ),
}


class PaymentError(Exception):
    pass


class HoldExpired(PaymentError):
    """The dates were released before the payment arrived: nothing is charged."""


class KeyReused(PaymentError):
    """An idempotency key that belongs to another booking."""


def decline_message(payment):
    return DECLINE_MESSAGES.get(payment.decline_code, DECLINE_MESSAGES["card_declined"])


def pay_booking(*, booking, card, idempotency_key, gateway=None, now=None):
    """Charge the booking's total and confirm it. Returns the Payment (succeeded or failed).

    The amount always comes from the booking, never from the form.
    """
    gateway = gateway or get_gateway()
    now = now or timezone.now()
    with transaction.atomic():
        # Every payment of this booking waits here for the previous one to finish.
        locked = Booking.objects.select_for_update().get(pk=booking.pk)

        existing = Payment.objects.filter(idempotency_key=idempotency_key).first()
        if existing is not None:
            if existing.booking_id != locked.pk:
                raise KeyReused
            return existing  # a retry of the same submission: same answer, no new charge

        if locked.status == Booking.Status.CONFIRMED:
            # Paid meanwhile from another tab: report that payment, do not charge again.
            return locked.payments.get(status=Payment.Status.SUCCEEDED)
        if not locked.is_hold_active(now):
            raise HoldExpired

        payment = Payment.objects.create(
            booking=locked,
            idempotency_key=idempotency_key,
            amount=locked.total,
            currency=locked.currency,
            card_brand=card.brand.name,
            card_last4=card.last4,
        )
        # With a real provider this call happens while the row is locked, which is what makes
        # "two tabs, one charge" hold; the provider's own idempotency key covers network retries.
        result = gateway.charge(
            amount=locked.total,
            currency=locked.currency,
            card=card,
            idempotency_key=idempotency_key,
            description=locked.reference,
        )
        if result.succeeded:
            payment.status = Payment.Status.SUCCEEDED
            payment.gateway_reference = result.reference
            locked.status = Booking.Status.CONFIRMED
            locked.confirmed_at = now
            locked.save(update_fields=["status", "confirmed_at", "updated_at"])
        else:
            payment.status = Payment.Status.FAILED
            payment.decline_code = result.decline_code
        payment.save(update_fields=["status", "gateway_reference", "decline_code", "updated_at"])

    booking.refresh_from_db()
    return payment
