import json
from datetime import timedelta
from decimal import Decimal

import pytest
import time_machine
from django.test import Client
from django.utils import timezone

from apps.bookings.models import Booking
from apps.properties.tests.factories import PropertyFactory, PropertyImageFactory

from .factories import BookingFactory

pytestmark = pytest.mark.django_db


def days(n):
    return (timezone.localdate() + timedelta(days=n)).isoformat()


@pytest.fixture
def prop():
    prop = PropertyFactory(
        max_guests=3,
        price_per_night=Decimal("100.00"),
        cleaning_fee=Decimal("20.00"),
        latitude=Decimal("-12.124567"),
        longitude=Decimal("-77.029123"),
    )
    PropertyImageFactory(property=prop)
    return prop


def detail_url(prop):
    return f"/es/properties/{prop.slug}/"


def book(client, prop, check_in=5, check_out=8, guests=2):
    return client.post(
        detail_url(prop),
        {"check_in": days(check_in), "check_out": days(check_out), "guests": guests},
    )


# Property page


def test_detail_page_shows_the_booking_card_and_the_approximate_location(client, prop):
    html = client.get(detail_url(prop)).text

    assert "Reservar ahora" in html
    assert 'data-lat="-12.125"' in html  # ~100 m, not the exact point
    assert "-12.124567" not in html


def test_detail_page_sends_the_taken_nights_to_the_calendar(client, prop):
    BookingFactory(
        property=prop,
        check_in=timezone.localdate() + timedelta(days=10),
        check_out=timezone.localdate() + timedelta(days=13),
    )

    html = client.get(detail_url(prop)).text
    data = json.loads(
        html.split('id="unavailable-dates" type="application/json">')[1].split("</script>")[0]
    )

    # Nights 10, 11 and 12: the check-out day (13) stays free for the next guest.
    assert data == [{"from": days(10), "to": days(12)}]


def test_dates_from_the_search_show_the_price_right_away(client, prop):
    html = client.get(
        detail_url(prop), {"check_in": days(5), "check_out": days(7), "guests": 2}
    ).text

    assert "US$ 100 × 2 noches" in html
    assert "US$ 220" in html  # 200 nights + 20 cleaning (the factory country has no taxes)


# Live quote


def test_quote_endpoint_returns_the_breakdown(client, prop):
    response = client.get(
        f"/en/properties/{prop.slug}/quote/",
        {"check_in": days(5), "check_out": days(7), "guests": 2},
    )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "nights": 2,
        "lines": [
            {"label": "US$ 100 × 2 nights", "amount": "US$ 200"},
            {"label": "Cleaning fee", "amount": "US$ 20"},
        ],
        "total": "US$ 220",
    }


def test_quote_endpoint_explains_why_dates_are_not_possible(client, prop):
    BookingFactory(
        property=prop,
        check_in=timezone.localdate() + timedelta(days=5),
        check_out=timezone.localdate() + timedelta(days=9),
    )

    response = client.get(
        f"/es/properties/{prop.slug}/quote/",
        {"check_in": days(6), "check_out": days(7), "guests": 2},
    )

    assert response.status_code == 400
    assert response.json()["errors"] == [
        "Estas fechas ya no están disponibles. Por favor elige otras fechas."
    ]


# "Book now" -> hold -> checkout


def test_booking_holds_the_dates_and_opens_the_checkout(client, prop):
    response = book(client, prop)

    booking = Booking.objects.get()
    assert response.status_code == 302
    assert response["Location"] == f"/es/checkout/{booking.reference}/"
    assert booking.status == Booking.Status.PENDING
    assert booking.guest is None  # anonymous visitor: they register in the checkout
    assert client.session["booking_holds"] == [booking.reference]


def test_invalid_booking_shows_the_errors_on_the_same_page(client, prop):
    response = book(client, prop, check_in=-2, check_out=1)

    assert response.status_code == 200
    assert "La llegada no puede ser una fecha pasada." in response.text
    assert not Booking.objects.exists()


def test_capacity_is_enforced_by_the_server(client, prop):
    response = book(client, prop, guests=5)

    assert "Esta propiedad admite hasta 3 huéspedes." in response.text
    assert not Booking.objects.exists()


def test_booking_taken_dates_is_refused(client, prop):
    BookingFactory(
        property=prop,
        check_in=timezone.localdate() + timedelta(days=6),
        check_out=timezone.localdate() + timedelta(days=9),
    )

    response = book(client, prop, check_in=5, check_out=7)

    assert "Estas fechas ya no están disponibles." in response.text
    assert Booking.objects.count() == 1


def test_booking_again_releases_the_previous_hold(client, prop):
    book(client, prop, check_in=5, check_out=8)
    book(client, prop, check_in=20, check_out=22)

    statuses = list(Booking.objects.order_by("check_in").values_list("status", flat=True))
    assert statuses == [Booking.Status.CANCELLED, Booking.Status.PENDING]


def test_checkout_shows_the_summary_and_the_countdown(client, prop):
    book(client, prop)
    booking = Booking.objects.get()

    html = client.get(f"/es/checkout/{booking.reference}/").text

    assert "data-hold-timer" in html
    assert prop.title_es in html
    assert "US$ 300 × 3 noches" not in html  # 3 nights at 100 = "US$ 100 × 3 noches"
    assert "US$ 100 × 3 noches" in html


def test_other_visitors_cannot_see_a_checkout(client, prop):
    book(client, prop)
    booking = Booking.objects.get()

    assert Client().get(f"/es/checkout/{booking.reference}/").status_code == 404


def test_expired_checkout_sends_the_visitor_back_with_their_dates(client, prop):
    book(client, prop, check_in=5, check_out=8)
    booking = Booking.objects.get()

    with time_machine.travel(timezone.now() + timedelta(minutes=16)):
        response = client.get(f"/es/checkout/{booking.reference}/", follow=True)

    assert response.redirect_chain[0][0] == (
        f"{detail_url(prop)}?check_in={days(5)}&check_out={days(8)}&guests=2"
    )
    assert "Se acabó el tiempo" in response.text


def test_change_dates_releases_the_hold(client, prop):
    book(client, prop)
    booking = Booking.objects.get()

    response = client.post(f"/es/checkout/{booking.reference}/release/")

    booking.refresh_from_db()
    assert booking.status == Booking.Status.CANCELLED
    assert response["Location"].startswith(detail_url(prop))
    assert client.session["booking_holds"] == []
