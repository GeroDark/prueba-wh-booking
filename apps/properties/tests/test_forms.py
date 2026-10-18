from datetime import timedelta

import pytest
from django.utils import timezone

from apps.properties.forms import SearchForm

from .factories import CityFactory, DistrictFactory, PropertyFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def bogota_virrey():
    city = CityFactory(slug="bogota", name_es="Bogotá")
    district = DistrictFactory(city=city, name_es="Virrey")
    PropertyFactory(district=district)
    return city, district


def days(n):
    return (timezone.localdate() + timedelta(days=n)).isoformat()


def test_only_cities_with_active_properties_are_offered(bogota_virrey):
    empty_city = CityFactory(slug="empty")
    DistrictFactory(city=empty_city)
    inactive_city = CityFactory(slug="inactive", is_active=False)
    PropertyFactory(district=DistrictFactory(city=inactive_city))

    cities = list(SearchForm().fields["city"].queryset)

    assert cities == [bogota_virrey[0]]


def test_districts_are_grouped_by_city(bogota_virrey):
    html = str(SearchForm()["district"])

    assert '<optgroup label="Bogotá">' in html
    assert ">Virrey</option>" in html


def test_a_complete_search_is_valid(bogota_virrey):
    city, district = bogota_virrey
    form = SearchForm(
        {
            "city": "bogota",
            "district": district.pk,
            "check_in": days(5),
            "check_out": days(8),
            "guests": 2,
        }
    )

    assert form.is_valid(), form.errors
    assert form.cleaned_data["city"] == city


def test_an_empty_search_is_valid():
    assert SearchForm({}).is_valid()


def test_district_must_belong_to_the_city(bogota_virrey):
    other_city = CityFactory(slug="lima")
    PropertyFactory(district=DistrictFactory(city=other_city))
    form = SearchForm({"city": "lima", "district": bogota_virrey[1].pk})

    assert not form.is_valid()
    assert "district" in form.errors


def test_district_alone_implies_its_city(bogota_virrey):
    form = SearchForm({"district": bogota_virrey[1].pk})

    assert form.is_valid()
    assert form.cleaned_data["city"] == bogota_virrey[0]


@pytest.mark.parametrize(
    ("data", "field"),
    [
        ({"check_in": days(3)}, "check_out"),
        ({"check_out": days(3)}, "check_in"),
        ({"check_in": days(-1), "check_out": days(2)}, "check_in"),
        ({"check_in": days(5), "check_out": days(5)}, "check_out"),
        ({"check_in": days(5), "check_out": days(4)}, "check_out"),
        ({"guests": 0}, "guests"),
        ({"guests": 17}, "guests"),
    ],
)
def test_invalid_searches_explain_the_problem(data, field):
    form = SearchForm(data)

    assert not form.is_valid()
    assert field in form.errors


def test_districts_by_city_feeds_the_dependent_select(bogota_virrey):
    _, district = bogota_virrey

    assert SearchForm().districts_by_city == {"bogota": [{"id": district.pk, "name": "Virrey"}]}
