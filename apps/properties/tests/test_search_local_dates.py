"""Search and booking agree on what "past" means: the date where the property is (D09).

Found by an external review: the search used the server's date (Lima) and the booking the
property's city date, so late at night the search accepted arrivals the booking rejected.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
import time_machine
from django.core.exceptions import ValidationError

from apps.bookings.services import hold_dates

from .factories import CityFactory, CountryFactory, DistrictFactory, PropertyFactory

pytestmark = pytest.mark.django_db

UTC = ZoneInfo("UTC")
# 04:30 UTC on 10 Oct 2026: still the 9th in Lima (23:30) and Mexico City (22:30),
# already the 10th in Madrid (06:30).
NIGHT_IN_LIMA = datetime(2026, 10, 10, 4, 30, tzinfo=UTC)
# 05:30 UTC: already the 10th in Lima (00:30), still the 9th in Mexico City (23:30).
JUST_AFTER_MIDNIGHT_IN_LIMA = datetime(2026, 10, 10, 5, 30, tzinfo=UTC)


@pytest.fixture
def places():
    def make(slug, tz, country_code):
        country = CountryFactory(code=country_code, name_es=slug, name_en=slug)
        city = CityFactory(slug=slug, timezone=tz, country=country)
        return PropertyFactory(district=DistrictFactory(city=city), max_guests=2)

    return {
        "lima": make("lima", "America/Lima", "pe"),
        "madrid": make("madrid", "Europe/Madrid", "es"),
        "mexico": make("mexico", "America/Mexico_City", "mx"),
    }


def search(client, city="", check_in="2026-10-09", check_out="2026-10-11"):
    response = client.get(
        "/es/search/", {"city": city, "check_in": check_in, "check_out": check_out}
    )
    return response, {prop.slug for prop in response.context["properties"]}


@time_machine.travel(NIGHT_IN_LIMA)
def test_the_reviewers_case_madrid_already_on_the_10th(client, places):
    response, found = search(client, city="madrid")

    assert "La llegada no puede ser una fecha pasada." in response.text
    with pytest.raises(ValidationError, match="pasada"):  # and booking agrees
        hold_dates(
            prop=places["madrid"],
            check_in=date(2026, 10, 9),
            check_out=date(2026, 10, 11),
            guests=1,
        )


@time_machine.travel(NIGHT_IN_LIMA)
def test_without_a_city_the_results_leave_out_cities_where_the_arrival_is_past(client, places):
    response, found = search(client)

    assert "fecha pasada" not in response.text
    assert found == {places["lima"].slug, places["mexico"].slug}  # not Madrid


@time_machine.travel(JUST_AFTER_MIDNIGHT_IN_LIMA)
def test_mexico_city_is_still_on_the_9th_after_midnight_in_lima(client, places):
    """The opposite case: the search used to reject an arrival the booking accepts."""
    response, found = search(client, city="mexico")

    assert "fecha pasada" not in response.text
    assert found == {places["mexico"].slug}
    booking = hold_dates(
        prop=places["mexico"], check_in=date(2026, 10, 9), check_out=date(2026, 10, 11), guests=1
    )
    assert booking.check_in == date(2026, 10, 9)


@time_machine.travel(JUST_AFTER_MIDNIGHT_IN_LIMA)
def test_every_page_tells_the_search_calendar_each_citys_first_arrival(client, places):
    """The calendar in the search bars offers the dates the server accepts (second review:
    it used the device's date, so in Lima after midnight it hid the 9th in Mexico City)."""
    response = client.get("/es/")

    assert '<script id="arrival-min-by-city" type="application/json">' in response.text
    assert response.context["footer_search_form"].arrival_min_by_city == {
        "lima": "2026-10-10",
        "madrid": "2026-10-10",
        "mexico": "2026-10-09",
        "": "2026-10-09",  # no city: the earliest
    }
