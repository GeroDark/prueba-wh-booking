import threading
import time
import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, connection, transaction
from django.utils import timezone

from apps.bookings.models import Booking
from apps.bookings.tests.factories import BookingFactory
from apps.payments.cards import VISA, Card
from apps.payments.gateways import SimulatedGateway
from apps.payments.models import Payment
from apps.payments.services import HoldExpired, KeyReused, pay_booking

pytestmark = pytest.mark.django_db

APPROVED = Card("4242424242424242", 12, 2030, "123", VISA)
DECLINED = Card("4000000000000002", 12, 2030, "123", VISA)


class CountingGateway(SimulatedGateway):
    """The simulated gateway, counting how many times a card was really charged."""

    def __init__(self, delay=0):
        self.charges = 0
        self.delay = delay
        self.lock = threading.Lock()

    def charge(self, **kwargs):
        with self.lock:
            self.charges += 1
        time.sleep(self.delay)  # a slow provider widens the race window
        return super().charge(**kwargs)


def held_booking(**kwargs):
    defaults = {
        "status": Booking.Status.PENDING,
        "expires_at": timezone.now() + timedelta(minutes=15),
        "total": Decimal("320.11"),
    }
    return BookingFactory(**{**defaults, **kwargs})


def test_an_approved_payment_confirms_the_booking():
    booking = held_booking()
    gateway = CountingGateway()

    payment = pay_booking(
        booking=booking, card=APPROVED, idempotency_key=uuid.uuid4(), gateway=gateway
    )

    booking.refresh_from_db()
    assert payment.status == Payment.Status.SUCCEEDED
    assert booking.status == Booking.Status.CONFIRMED
    assert booking.confirmed_at is not None
    assert payment.amount == Decimal("320.11")  # from the booking, never from the form
    assert gateway.charges == 1


def test_only_the_brand_and_last_four_digits_are_stored():
    payment = pay_booking(booking=held_booking(), card=APPROVED, idempotency_key=uuid.uuid4())

    stored = " ".join(str(value) for value in Payment.objects.values().get().values())
    columns = {field.name for field in Payment._meta.fields}
    assert (payment.card_brand, payment.card_last4) == ("Visa", "4242")
    assert "4242424242424242" not in stored
    assert not columns & {"card_number", "number", "expiry", "exp_month", "exp_year", "cvc"}


def test_a_declined_payment_is_recorded_and_the_hold_stays():
    booking = held_booking()

    payment = pay_booking(booking=booking, card=DECLINED, idempotency_key=uuid.uuid4())

    booking.refresh_from_db()
    assert payment.status == Payment.Status.FAILED
    assert payment.decline_code == "card_declined"
    assert booking.status == Booking.Status.PENDING


def test_declined_then_retried_with_another_card():
    booking = held_booking()
    pay_booking(booking=booking, card=DECLINED, idempotency_key=uuid.uuid4())

    payment = pay_booking(booking=booking, card=APPROVED, idempotency_key=uuid.uuid4())

    assert payment.status == Payment.Status.SUCCEEDED
    assert booking.payments.count() == 2  # every attempt is kept


def test_same_key_twice_charges_once():
    """Double click, reload or network retry: the same form reaches the server twice."""
    booking = held_booking()
    gateway = CountingGateway()
    key = uuid.uuid4()

    first = pay_booking(booking=booking, card=APPROVED, idempotency_key=key, gateway=gateway)
    second = pay_booking(booking=booking, card=APPROVED, idempotency_key=key, gateway=gateway)

    assert first == second
    assert gateway.charges == 1
    assert Payment.objects.count() == 1


def test_same_key_after_a_decline_returns_the_decline_without_charging_again():
    booking = held_booking()
    gateway = CountingGateway()
    key = uuid.uuid4()
    pay_booking(booking=booking, card=DECLINED, idempotency_key=key, gateway=gateway)

    again = pay_booking(booking=booking, card=APPROVED, idempotency_key=key, gateway=gateway)

    assert again.status == Payment.Status.FAILED
    assert gateway.charges == 1


def test_a_second_tab_with_a_new_key_does_not_charge_a_paid_booking():
    booking = held_booking()
    gateway = CountingGateway()
    first = pay_booking(
        booking=booking, card=APPROVED, idempotency_key=uuid.uuid4(), gateway=gateway
    )

    second = pay_booking(
        booking=booking, card=APPROVED, idempotency_key=uuid.uuid4(), gateway=gateway
    )

    assert second == first
    assert gateway.charges == 1


def test_an_expired_hold_is_not_charged():
    booking = held_booking(expires_at=timezone.now() - timedelta(seconds=1))
    gateway = CountingGateway()

    with pytest.raises(HoldExpired):
        pay_booking(booking=booking, card=APPROVED, idempotency_key=uuid.uuid4(), gateway=gateway)

    assert gateway.charges == 0
    assert not Payment.objects.exists()


def test_a_key_of_another_booking_is_refused():
    key = uuid.uuid4()
    pay_booking(booking=held_booking(), card=DECLINED, idempotency_key=key)

    with pytest.raises(KeyReused):
        pay_booking(booking=held_booking(), card=APPROVED, idempotency_key=key)


def test_a_real_card_is_never_approved_by_the_demo():
    real_looking = Card("4111111111111111", 12, 2030, "123", VISA)

    payment = pay_booking(booking=held_booking(), card=real_looking, idempotency_key=uuid.uuid4())

    assert payment.status == Payment.Status.FAILED
    assert payment.decline_code == "test_card_required"


def test_database_allows_only_one_successful_payment_per_booking():
    booking = held_booking()
    fields = {"amount": Decimal("1"), "card_brand": "Visa", "card_last4": "4242"}
    Payment.objects.create(
        booking=booking, idempotency_key=uuid.uuid4(), status="succeeded", **fields
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        Payment.objects.create(
            booking=booking, idempotency_key=uuid.uuid4(), status="succeeded", **fields
        )


# Concurrency: two tabs press "Complete booking" at the same moment


@pytest.mark.django_db(transaction=True)
def test_two_tabs_paying_at_the_same_time_charge_once():
    booking = held_booking()
    gateway = CountingGateway(delay=0.2)
    start = threading.Barrier(2)
    results = []

    def pay():
        start.wait()
        try:
            payment = pay_booking(
                booking=booking, card=APPROVED, idempotency_key=uuid.uuid4(), gateway=gateway
            )
            results.append(payment.pk)
        finally:
            connection.close()

    threads = [threading.Thread(target=pay) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert gateway.charges == 1
    assert len(set(results)) == 1  # both tabs see the same payment
    assert Payment.objects.filter(status=Payment.Status.SUCCEEDED).count() == 1
