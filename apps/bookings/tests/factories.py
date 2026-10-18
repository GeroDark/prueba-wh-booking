from datetime import date, timedelta

import factory
from django.utils import timezone

from apps.bookings.models import Booking
from apps.properties.tests.factories import PropertyFactory


class BookingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Booking

    property = factory.SubFactory(PropertyFactory)
    status = Booking.Status.CONFIRMED
    check_in = factory.LazyFunction(lambda: timezone.localdate() + timedelta(days=10))
    check_out = factory.LazyAttribute(lambda booking: booking.check_in + timedelta(days=5))
    guests = 2


def on(day):
    """Dates in the D06 examples: on(10) is the 10th of a fixed future month."""
    return date(2030, 1, day)
