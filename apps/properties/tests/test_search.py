import json
from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.bookings.models import Booking
from apps.bookings.tests.factories import BookingFactory
from apps.properties.models import Property

from .factories import (
    CityFactory,
    CountryFactory,
    DistrictFactory,
    PropertyFactory,
    PropertyImageFactory,
)

pytestmark = pytest.mark.django_db


def days(n):
    return timezone.localdate() + timedelta(days=n)


@pytest.fixture
def catalog():
    """Two cities in two countries; Lima has two districts."""
    peru = CountryFactory(code="pe", slug="peru", name_es="Perú")
    colombia = CountryFactory(code="co", slug="colombia", name_es="Colombia")
    lima = CityFactory(country=peru, slug="lima", name_es="Lima", name_en="Lima")
    bogota = CityFactory(country=colombia, slug="bogota", name_es="Bogotá")
    miraflores = DistrictFactory(city=lima, slug="miraflores", name_es="Miraflores")
    barranco = DistrictFactory(city=lima, slug="barranco", name_es="Barranco")
    chico = DistrictFactory(city=bogota, slug="chico", name_es="Chicó")
    return {
        "miraflores_small": PropertyFactory(
            district=miraflores,
            max_guests=2,
            latitude=Decimal("-12.124567"),
            longitude=Decimal("-77.029123"),
        ),
        "miraflores_big": PropertyFactory(district=miraflores, max_guests=6),
        "barranco": PropertyFactory(district=barranco, max_guests=4),
        "chico": PropertyFactory(district=chico, max_guests=3),
    }


def slugs(queryset):
    return {prop.slug for prop in queryset}


# QuerySet filters


def test_filters_by_country_city_and_district(catalog):
    peru = catalog["barranco"].district.city.country
    lima = catalog["barranco"].district.city
    barranco = catalog["barranco"].district

    assert slugs(Property.objects.search(country=peru)) == slugs(
        [catalog["miraflores_small"], catalog["miraflores_big"], catalog["barranco"]]
    )
    assert len(Property.objects.search(city=lima)) == 3
    assert list(Property.objects.search(district=barranco)) == [catalog["barranco"]]


def test_filters_by_capacity(catalog):
    result = Property.objects.search(guests=4)

    assert slugs(result) == slugs([catalog["miraflores_big"], catalog["barranco"]])


def test_excludes_properties_booked_on_those_dates(catalog):
    BookingFactory(property=catalog["chico"], check_in=days(10), check_out=days(15))

    result = Property.objects.search(check_in=days(12), check_out=days(14))

    assert catalog["chico"] not in result
    assert len(result) == 3


def test_a_stay_ending_on_arrival_day_does_not_block(catalog):
    BookingFactory(property=catalog["chico"], check_in=days(10), check_out=days(15))

    assert catalog["chico"] in Property.objects.search(check_in=days(15), check_out=days(18))


def test_expired_holds_and_cancelled_bookings_do_not_block(catalog):
    BookingFactory(
        property=catalog["chico"],
        status=Booking.Status.PENDING,
        expires_at=timezone.now() - timedelta(minutes=1),
        check_in=days(10),
        check_out=days(15),
    )
    BookingFactory(
        property=catalog["barranco"],
        status=Booking.Status.CANCELLED,
        check_in=days(10),
        check_out=days(15),
    )

    result = Property.objects.search(check_in=days(10), check_out=days(15))

    assert {catalog["chico"], catalog["barranco"]} <= set(result)


def test_a_live_hold_blocks_like_a_confirmed_booking(catalog):
    BookingFactory(
        property=catalog["chico"],
        status=Booking.Status.PENDING,
        expires_at=timezone.now() + timedelta(minutes=10),
        check_in=days(10),
        check_out=days(15),
    )

    assert catalog["chico"] not in Property.objects.search(check_in=days(11), check_out=days(12))


def test_filters_combine(catalog):
    lima = catalog["barranco"].district.city
    BookingFactory(property=catalog["miraflores_big"], check_in=days(5), check_out=days(9))

    result = Property.objects.search(city=lima, guests=3, check_in=days(6), check_out=days(8))

    assert list(result) == [catalog["barranco"]]


# Results page


def test_results_page_applies_the_url_filters(client, catalog):
    html = client.get("/es/search/", {"city": "lima", "guests": 5}).text

    assert catalog["miraflores_big"].title_es in html
    assert catalog["barranco"].title_es not in html
    assert catalog["chico"].title_es not in html


def test_invalid_filters_are_reported_and_valid_ones_still_apply(client, catalog):
    response = client.get(
        "/es/search/", {"city": "bogota", "check_in": days(5), "check_out": days(2)}
    )
    html = response.text

    assert "La salida debe ser posterior a la llegada." in html
    assert catalog["chico"].title_es in html
    assert catalog["barranco"].title_es not in html


def test_no_results_shows_a_helpful_empty_state(client, catalog):
    html = client.get("/es/search/", {"guests": 16}).text

    assert "Ninguna propiedad coincide con tu búsqueda" in html
    assert 'href="/es/search/"' in html


def test_pagination_keeps_the_filters(client, catalog):
    district = catalog["chico"].district
    for _ in range(11):
        PropertyFactory(district=district, max_guests=3)

    html = client.get("/es/search/", {"city": "bogota", "guests": 2}).text

    assert "?city=bogota&amp;guests=2&amp;page=2" in html


def test_map_shows_exactly_the_properties_of_the_page_with_rounded_coordinates(client, catalog):
    response = client.get("/es/search/", {"city": "lima"})
    markers = json.loads(
        response.text.split('id="map-markers" type="application/json">')[1].split("</script>")[0]
    )

    with_location = [m for m in markers if m["id"] == catalog["miraflores_small"].pk]
    assert len(with_location) == 1
    marker = with_location[0]
    assert (marker["lat"], marker["lng"]) == (-12.125, -77.029)  # ~100 m, not the exact address
    assert marker["url"] == f"/es/properties/{catalog['miraflores_small'].slug}/"
    assert marker["price"] == "US$ 100"
    shown_ids = {prop.pk for prop in response.context["properties"]}
    assert {m["id"] for m in markers} <= shown_ids


def test_results_query_count_does_not_grow_with_results(client, catalog):
    def count_queries():
        with CaptureQueriesContext(connection) as queries:
            assert client.get("/es/search/").status_code == 200
        return len(queries)

    count_queries()  # warm-up: the first request creates the site settings row
    before = count_queries()
    for prop in Property.objects.all():
        PropertyImageFactory(property=prop)
    PropertyFactory.create_batch(4, district=catalog["chico"].district)

    assert count_queries() == before


def test_summary_lists_only_the_active_filters(client, catalog):
    only_guests = client.get("/es/search/", {"guests": 2}).context["summary"]
    full = client.get(
        "/en/search/",
        {"city": "lima", "check_in": days(5), "check_out": days(9), "guests": 1},
    ).context["summary"]

    assert only_guests == ["2 huéspedes"]
    assert full[0] == "Lima"
    assert full[2] == "1 guest"


def test_invalid_filters_say_which_field_is_wrong_in_the_site_tone(client):
    html = client.get("/es/search/?check_in=abc&guests=99&city=nope").text

    assert "Llegada: Ingresa una fecha válida." in html
    assert "Huéspedes: Ingresa un número menor o igual a 16." in html
    assert "Elige una de las opciones disponibles." in html
    assert "Introduzca" not in html and "Asegúrese" not in html and "Escoja" not in html
