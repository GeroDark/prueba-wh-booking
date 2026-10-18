from datetime import UTC, datetime
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone, translation

from apps.properties.models import Property

from .factories import (
    CityFactory,
    PropertyFactory,
    PropertyImageFactory,
    TaxFactory,
)

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "changes",
    [
        {"price_per_night": Decimal("0")},
        {"cleaning_fee": Decimal("-1")},
        {"max_guests": 0},
    ],
)
def test_database_rejects_invalid_property_values(changes):
    prop = PropertyFactory()

    with pytest.raises(IntegrityError), transaction.atomic():
        Property.objects.filter(pk=prop.pk).update(**changes)


@pytest.mark.parametrize("rate", [Decimal("0"), Decimal("100.01")])
def test_database_rejects_tax_rates_outside_range(rate):
    with pytest.raises(IntegrityError), transaction.atomic():
        TaxFactory(rate=rate)


def test_city_rejects_unknown_time_zones():
    city = CityFactory.build(timezone="America/Atlantis")

    with pytest.raises(ValidationError, match="America/Atlantis"):
        city.full_clean(exclude=["country"])


def test_local_today_depends_on_the_city_time_zone(monkeypatch):
    # 2026-10-20 04:30 UTC is still the 19th in Lima (UTC-5) but already the 20th in Madrid.
    monkeypatch.setattr(timezone, "now", lambda: datetime(2026, 10, 20, 4, 30, tzinfo=UTC))

    lima = CityFactory.build(timezone="America/Lima")
    madrid = CityFactory.build(timezone="Europe/Madrid")

    assert lima.local_today().day == 19
    assert madrid.local_today().day == 20


def test_translated_fields_follow_the_active_language():
    prop = PropertyFactory(title_es="Ático en Malasaña", title_en="Penthouse in Malasaña")

    with translation.override("es"):
        assert prop.title == "Ático en Malasaña"
    with translation.override("en"):
        assert prop.title == "Penthouse in Malasaña"


def test_missing_english_translation_falls_back_to_spanish():
    prop = PropertyFactory(title_es="Ático en Malasaña", title_en="")

    with translation.override("en"):
        assert prop.title == "Ático en Malasaña"


def test_active_and_featured_querysets():
    featured = PropertyFactory(is_featured=True)
    PropertyFactory(is_featured=False)
    PropertyFactory(is_featured=True, is_active=False)

    assert list(Property.objects.active().featured()) == [featured]


def test_cover_image_is_the_first_by_order():
    prop = PropertyFactory()
    second = PropertyImageFactory(property=prop, order=2)
    first = PropertyImageFactory(property=prop, order=1)

    assert prop.cover_image == first
    assert second != first


def test_card_data_is_loaded_in_a_fixed_number_of_queries(django_assert_num_queries):
    for _ in range(3):
        PropertyImageFactory()

    # 1 query for properties + location (select_related) and 1 for all their images.
    with django_assert_num_queries(2):
        for prop in Property.objects.with_card_data():
            _ = (prop.city.country.name, prop.cover_image)


def test_default_ordering_puts_featured_first():
    PropertyFactory(title_es="A normal", is_featured=False)
    featured = PropertyFactory(title_es="Z destacado", is_featured=True)

    assert Property.objects.first() == featured
