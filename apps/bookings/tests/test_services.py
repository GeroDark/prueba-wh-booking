import threading
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
import time_machine
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.utils import timezone

from apps.bookings.models import Booking
from apps.bookings.services import expire_holds, hold_dates, is_available, validate_stay
from apps.properties.tests.factories import CityFactory, DistrictFactory, PropertyFactory

from .factories import BookingFactory

pytestmark = pytest.mark.django_db


def days(n):
    return timezone.localdate() + timedelta(days=n)


@pytest.fixture
def prop():
    return PropertyFactory(max_guests=3, price_per_night=Decimal("100.00"))


def error_codes(error):
    return {field: [e.code for e in errors] for field, errors in error.error_dict.items()}


# Rules that do not depend on other bookings (validate_stay)


@pytest.mark.parametrize(
    ("check_in", "check_out", "guests", "field", "code"),
    [
        (-1, 2, 2, "check_in", "past"),
        (5, 5, 2, "check_out", "order"),
        (5, 4, 2, "check_out", "order"),
        (5, 40, 2, "check_out", "too_long"),
        (400, 403, 2, "check_in", "too_far"),
        (5, 8, 4, "guests", "capacity"),
        (5, 8, 0, "guests", "guests"),
    ],
)
def test_invalid_stays_are_rejected_with_a_reason(prop, check_in, check_out, guests, field, code):
    with pytest.raises(ValidationError) as error:
        validate_stay(prop, days(check_in), days(check_out), guests)

    assert error_codes(error.value)[field] == [code]


def test_today_is_a_valid_check_in(prop):
    validate_stay(prop, prop.district.city.local_today(), days(3), 2)


@time_machine.travel(datetime(2030, 3, 10, 4, 30, tzinfo=UTC), tick=False)
def test_past_is_decided_in_the_property_time_zone():
    """04:30 UTC on 10 March: still the 9th in Lima, already the 10th in Madrid (D09)."""
    lima = PropertyFactory(district=DistrictFactory(city=CityFactory(timezone="America/Lima")))
    madrid = PropertyFactory(district=DistrictFactory(city=CityFactory(timezone="Europe/Madrid")))
    ninth = datetime(2030, 3, 9).date()

    validate_stay(lima, ninth, ninth + timedelta(days=2), 1)
    with pytest.raises(ValidationError):
        validate_stay(madrid, ninth, ninth + timedelta(days=2), 1)


# Holds


def test_hold_blocks_the_dates_for_the_configured_minutes(prop, settings):
    settings.BOOKING_HOLD_MINUTES = 15
    before = timezone.now()

    booking = hold_dates(prop=prop, check_in=days(5), check_out=days(8), guests=2)

    assert booking.status == Booking.Status.PENDING
    assert timedelta(minutes=14) < booking.expires_at - before <= timedelta(minutes=15, seconds=5)
    assert not is_available(prop, days(6), days(7))


def test_hold_freezes_the_price_breakdown(prop):
    booking = hold_dates(prop=prop, check_in=days(5), check_out=days(8), guests=2)
    prop.price_per_night = Decimal("999.00")
    prop.save()

    booking.refresh_from_db()
    assert booking.lines.first().amount == Decimal("300.00")
    assert booking.total == sum(line.amount for line in booking.lines.all())
    assert booking.lines.first().label_en == "US$ 100 × 3 nights"


def test_hold_is_refused_when_the_dates_overlap_a_booking(prop):
    BookingFactory(property=prop, check_in=days(10), check_out=days(15))

    with pytest.raises(ValidationError) as error:
        hold_dates(prop=prop, check_in=days(14), check_out=days(16), guests=2)

    assert error.value.code == "unavailable"


def test_hold_can_start_the_day_another_stay_ends(prop):
    BookingFactory(property=prop, check_in=days(10), check_out=days(15))

    booking = hold_dates(prop=prop, check_in=days(15), check_out=days(18), guests=2)

    assert booking.pk


def test_an_expired_hold_frees_the_dates(prop):
    first = hold_dates(prop=prop, check_in=days(5), check_out=days(8), guests=2)

    with time_machine.travel(timezone.now() + timedelta(minutes=16)):
        assert is_available(prop, days(5), days(8))
        second = hold_dates(prop=prop, check_in=days(5), check_out=days(8), guests=1)

    first.refresh_from_db()
    assert first.status == Booking.Status.EXPIRED
    assert second.status == Booking.Status.PENDING


def test_a_new_hold_releases_the_visitors_previous_one(prop):
    first = hold_dates(prop=prop, check_in=days(5), check_out=days(8), guests=2)
    other = PropertyFactory()

    hold_dates(
        prop=other, check_in=days(5), check_out=days(8), guests=1, released_holds=[first.reference]
    )

    first.refresh_from_db()
    assert first.status == Booking.Status.CANCELLED
    assert is_available(prop, days(5), days(8))


def test_holds_on_inactive_properties_are_refused(prop):
    prop.is_active = False
    prop.save()

    with pytest.raises(ValidationError) as error:
        hold_dates(prop=prop, check_in=days(5), check_out=days(8), guests=2)

    assert error.value.code == "unavailable"


def test_expire_holds_marks_only_stale_holds(prop):
    stale = BookingFactory(
        property=prop,
        status=Booking.Status.PENDING,
        expires_at=timezone.now() - timedelta(minutes=1),
        check_in=days(5),
        check_out=days(7),
    )
    live = BookingFactory(
        property=prop,
        status=Booking.Status.PENDING,
        expires_at=timezone.now() + timedelta(minutes=10),
        check_in=days(8),
        check_out=days(9),
    )

    assert expire_holds() == 1
    stale.refresh_from_db()
    live.refresh_from_db()
    assert (stale.status, live.status) == (Booking.Status.EXPIRED, Booking.Status.PENDING)


# Database guarantee (PostgreSQL exclusion constraint)


@pytest.mark.skipif(
    connection.vendor != "postgresql", reason="exclusion constraints need PostgreSQL"
)
def test_database_rejects_overlapping_active_bookings(prop):
    BookingFactory(property=prop, check_in=days(10), check_out=days(15))

    with pytest.raises(IntegrityError), transaction.atomic():
        BookingFactory(property=prop, check_in=days(12), check_out=days(13))


@pytest.mark.skipif(
    connection.vendor != "postgresql", reason="exclusion constraints need PostgreSQL"
)
def test_cancelled_and_expired_bookings_do_not_occupy_dates_in_the_database(prop):
    BookingFactory(
        property=prop, check_in=days(10), check_out=days(15), status=Booking.Status.CANCELLED
    )
    BookingFactory(
        property=prop, check_in=days(10), check_out=days(15), status=Booking.Status.EXPIRED
    )

    BookingFactory(property=prop, check_in=days(10), check_out=days(15))  # no error


# Concurrency: two visitors press "Book now" at the same moment


@pytest.mark.django_db(transaction=True)
def test_only_one_of_two_simultaneous_holds_wins():
    prop = PropertyFactory(max_guests=4)
    start = threading.Barrier(2)
    results = []

    def book():
        start.wait()  # release both threads at the same time
        try:
            booking = hold_dates(prop=prop, check_in=days(20), check_out=days(23), guests=2)
            results.append(booking.reference)
        except ValidationError:
            results.append("refused")
        finally:
            connection.close()  # each thread has its own database connection

    threads = [threading.Thread(target=book) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert results.count("refused") == 1
    assert Booking.objects.filter(property=prop, status=Booking.Status.PENDING).count() == 1
