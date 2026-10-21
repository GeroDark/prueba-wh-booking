"""My bookings (D44): only the guest's own bookings, grouped as waiting for payment, upcoming
and past, with "past" decided by the city's local date (D09)."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
import time_machine
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.bookings.models import Booking
from apps.properties.tests.factories import CityFactory, DistrictFactory, PropertyFactory

from .factories import BookingFactory

pytestmark = pytest.mark.django_db

User = get_user_model()
MY_BOOKINGS = "/es/bookings/"


@pytest.fixture
def ana(client):
    user = User.objects.create_user("ana@mail.com", "Luna-Mar-Cielo-7", full_name="Ana Torres")
    client.force_login(user)
    return user


def groups(response):
    return {
        name: [booking.reference for booking in response.context[name]]
        for name in ("pending", "upcoming", "past")
    }


def days(n):
    return timezone.localdate() + timedelta(days=n)


def test_visitors_are_sent_to_sign_in_and_back(client):
    response = client.get(MY_BOOKINGS)

    assert response.status_code == 302
    assert response["Location"] == f"/es/accounts/login/?next={MY_BOOKINGS}"


def test_bookings_are_grouped(client, ana):
    upcoming = BookingFactory(guest=ana, check_in=days(10), check_out=days(12))
    in_progress = BookingFactory(guest=ana, check_in=days(-1), check_out=days(2))
    past = BookingFactory(guest=ana, check_in=days(-10), check_out=days(-7))
    older = BookingFactory(guest=ana, check_in=days(-40), check_out=days(-35))
    held = BookingFactory(
        guest=ana,
        status=Booking.Status.PENDING,
        expires_at=timezone.now() + timedelta(minutes=10),
    )

    response = client.get(MY_BOOKINGS)

    assert groups(response) == {
        "pending": [held.reference],
        "upcoming": [in_progress.reference, upcoming.reference],  # soonest first
        "past": [past.reference, older.reference],  # most recent first
    }
    assert f"/es/checkout/{held.reference}/" in response.text  # continue to payment
    assert f"/es/bookings/{upcoming.reference}/" in response.text


def test_only_the_guests_own_bookings_and_never_dead_holds(client, ana):
    someone_else = User.objects.create_user("beto@mail.com", "Luna-Mar-Cielo-7")
    mine = BookingFactory(guest=ana)
    BookingFactory(guest=someone_else)
    BookingFactory(  # an anonymous visitor's hold
        guest=None, status=Booking.Status.PENDING, expires_at=timezone.now() + timedelta(days=1)
    )
    BookingFactory(
        guest=ana,
        status=Booking.Status.PENDING,
        expires_at=timezone.now() - timedelta(minutes=1),  # expired, status not updated yet
    )
    BookingFactory(guest=ana, status=Booking.Status.EXPIRED)
    BookingFactory(guest=ana, status=Booking.Status.CANCELLED)

    response = client.get(MY_BOOKINGS)

    assert groups(response) == {"pending": [], "upcoming": [mine.reference], "past": []}


# 23:30 on 9 Jan 2030 in Lima = 05:30 on the 10th in Madrid.
NIGHT_IN_LIMA = datetime(2030, 1, 10, 4, 30, tzinfo=ZoneInfo("UTC"))


@time_machine.travel(NIGHT_IN_LIMA, tick=False)
def test_past_is_decided_with_the_citys_date(client, ana):
    """Both stays end on the 10th: in Madrid that day has started, in Lima it has not."""
    madrid = PropertyFactory(district=DistrictFactory(city=CityFactory(timezone="Europe/Madrid")))
    lima = PropertyFactory(district=DistrictFactory(city=CityFactory(timezone="America/Lima")))
    in_madrid = BookingFactory(
        guest=ana, property=madrid, check_in=date(2030, 1, 7), check_out=date(2030, 1, 10)
    )
    in_lima = BookingFactory(
        guest=ana, property=lima, check_in=date(2030, 1, 7), check_out=date(2030, 1, 10)
    )
    client.force_login(ana)  # the fixture's session belongs to today, not to 2030

    response = client.get(MY_BOOKINGS)

    assert groups(response)["past"] == [in_madrid.reference]
    assert groups(response)["upcoming"] == [in_lima.reference]


def test_the_page_is_never_cached(client, ana):
    """Shared computer: after signing out, Back must not show the previous guest's bookings."""
    response = client.get(MY_BOOKINGS)

    assert "no-store" in response["Cache-Control"]
    assert "private" in response["Cache-Control"]


def test_without_bookings_it_invites_to_search(client, ana):
    response = client.get(MY_BOOKINGS)

    assert "Aún no tienes reservas" in response.text
    assert 'href="/es/search/"' in response.text


def test_english(client, ana):
    BookingFactory(guest=ana)

    response = client.get("/en/bookings/")

    assert "My bookings" in response.text
    assert "Upcoming stays" in response.text


def test_the_header_links_to_it_only_when_signed_in(client):
    assert MY_BOOKINGS not in client.get("/es/").text

    user = User.objects.create_user("ana@mail.com", "Luna-Mar-Cielo-7", full_name="Ana Torres")
    client.force_login(user)

    assert f'href="{MY_BOOKINGS}"' in client.get("/es/").text


def test_queries_do_not_grow_with_the_number_of_bookings(client, ana):
    """No query per booking (N+1): photos, district, city and country come in bulk."""
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    def queries_for(count):
        Booking.objects.all().delete()
        for n in range(count):
            BookingFactory(guest=ana, check_in=days(10 + 7 * n), check_out=days(12 + 7 * n))
        with CaptureQueriesContext(connection) as captured:
            response = client.get(MY_BOOKINGS)
        assert len(groups(response)["upcoming"]) == count
        return len(captured)

    client.get(MY_BOOKINGS)  # warm-up: the first request also fills a few one-time caches
    one = queries_for(1)
    assert queries_for(8) == one
