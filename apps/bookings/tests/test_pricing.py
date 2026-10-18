from datetime import date
from decimal import Decimal

import pytest
from django.utils import translation

from apps.bookings.pricing import quote_stay
from apps.properties.tests.factories import (
    CityFactory,
    CountryFactory,
    DistrictFactory,
    PropertyFactory,
    TaxFactory,
)

pytestmark = pytest.mark.django_db

CHECK_IN, CHECK_OUT = date(2030, 1, 10), date(2030, 1, 15)  # 5 nights


@pytest.fixture
def mexico_property():
    mexico = CountryFactory(code="mx", slug="mexico", name_es="México")
    TaxFactory(country=mexico, name_es="IVA", name_en="VAT", rate=Decimal("16.00"))
    TaxFactory(
        country=mexico, name_es="Impuesto de ciudad", name_en="City tax", rate=Decimal("3.00")
    )
    TaxFactory(country=mexico, name_es="Inactivo", rate=Decimal("50.00"), is_active=False)
    district = DistrictFactory(city=CityFactory(country=mexico))
    return PropertyFactory(
        district=district, price_per_night=Decimal("83.00"), cleaning_fee=Decimal("20.00")
    )


def test_quote_adds_nights_cleaning_and_country_taxes(mexico_property):
    quote = quote_stay(mexico_property, CHECK_IN, CHECK_OUT)

    amounts = [line.amount for line in quote.lines]
    # 5 × 83 = 415; + 20 cleaning = 435 taxable; 16 % = 69.60; 3 % = 13.05
    assert amounts == [Decimal("415.00"), Decimal("20.00"), Decimal("69.60"), Decimal("13.05")]
    assert quote.total == Decimal("517.65")
    assert quote.nights == 5


def test_inactive_taxes_are_ignored(mexico_property):
    labels = [line.labels["es"] for line in quote_stay(mexico_property, CHECK_IN, CHECK_OUT).lines]

    assert not any("Inactivo" in label for label in labels)


def test_lines_are_labelled_in_both_languages(mexico_property):
    lines = quote_stay(mexico_property, CHECK_IN, CHECK_OUT).lines

    assert lines[0].labels == {"es": "US$ 83 × 5 noches", "en": "US$ 83 × 5 nights"}
    assert lines[1].labels == {"es": "Tarifa de limpieza", "en": "Cleaning fee"}
    assert lines[2].labels == {"es": "IVA (16%)", "en": "VAT (16%)"}
    with translation.override("en"):
        assert lines[3].label == "City tax (3%)"


def test_taxes_are_rounded_half_up_to_cents():
    country = CountryFactory(code="pe", slug="peru")
    TaxFactory(country=country, rate=Decimal("18.00"))
    prop = PropertyFactory(
        district=DistrictFactory(city=CityFactory(country=country)),
        price_per_night=Decimal("10.25"),
        cleaning_fee=Decimal("0"),
    )

    quote = quote_stay(prop, CHECK_IN, date(2030, 1, 11))  # 1 night

    # 10.25 × 18 % = 1.845 -> 1.85 (half up), and no cleaning line when the fee is zero
    assert [line.amount for line in quote.lines] == [Decimal("10.25"), Decimal("1.85")]
    assert quote.total == Decimal("12.10")
