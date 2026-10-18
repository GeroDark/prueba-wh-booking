import re
from datetime import timedelta

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.bookings.models import Booking, generate_reference

from .factories import BookingFactory, on

pytestmark = pytest.mark.django_db


def test_reference_is_random_readable_and_unique():
    references = {generate_reference() for _ in range(500)}

    assert len(references) == 500
    assert all(re.fullmatch(r"WH-[2-9A-HJKMNP-Z]{8}", ref) for ref in references)


def test_nights_between_check_in_and_check_out():
    assert BookingFactory.build(check_in=on(10), check_out=on(15)).nights == 5


@pytest.mark.parametrize(
    "changes",
    [{"check_out": on(10)}, {"check_out": on(9)}, {"guests": 0}],
)
def test_database_rejects_impossible_bookings(changes):
    booking = BookingFactory(check_in=on(10), check_out=on(15))

    with pytest.raises(IntegrityError), transaction.atomic():
        Booking.objects.filter(pk=booking.pk).update(**changes)


# D06: an existing stay A from the 10th to the 15th (nights 10-14).
@pytest.mark.parametrize(
    ("check_in", "check_out", "overlaps"),
    [
        (15, 18, False),  # A leaves the morning of the 15th, the new guest arrives that afternoon
        (5, 10, False),  # the new stay ends the day A begins
        (14, 16, True),  # both need the night of the 14th
        (8, 11, True),  # both need the night of the 10th
        (11, 13, True),  # inside A
        (5, 20, True),  # contains A
    ],
)
def test_overlap_uses_half_open_intervals(check_in, check_out, overlaps):
    BookingFactory(check_in=on(10), check_out=on(15))

    result = Booking.objects.overlapping(on(check_in), on(check_out)).exists()

    assert result is overlaps


@pytest.mark.parametrize(
    ("status", "expires_in_minutes", "blocks"),
    [
        (Booking.Status.CONFIRMED, None, True),
        (Booking.Status.PENDING, 10, True),  # live hold
        (Booking.Status.PENDING, -1, False),  # expired hold: free without any background job
        (Booking.Status.EXPIRED, None, False),
        (Booking.Status.CANCELLED, None, False),
    ],
)
def test_which_bookings_block_their_dates(status, expires_in_minutes, blocks):
    expires_at = (
        timezone.now() + timedelta(minutes=expires_in_minutes)
        if expires_in_minutes is not None
        else None
    )
    BookingFactory(status=status, expires_at=expires_at)

    assert Booking.objects.blocking().exists() is blocks
