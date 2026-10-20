"""End-to-end tests: a real browser (Playwright) against Django's live test server.

They check that templates, JavaScript (calendar, live quote, form hints) and the server work
together, which unit tests cannot. Run with `pytest -m e2e` after `python -m playwright install
chromium`; CI runs them in their own job.
"""

import os
from decimal import Decimal

import pytest

from apps.properties.tests.factories import (
    CityFactory,
    CountryFactory,
    DistrictFactory,
    PropertyFactory,
)

# Playwright's sync API runs an event loop in the test thread; the ORM calls made by the test
# itself (fixtures, assertions) are still plain synchronous code.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")


@pytest.fixture
def prop(transactional_db):
    country = CountryFactory(code="co", name_es="Colombia", name_en="Colombia", slug="colombia")
    city = CityFactory(
        country=country,
        slug="bogota",
        name_es="Bogotá",
        name_en="Bogota",
        timezone="America/Bogota",
    )
    district = DistrictFactory(city=city, name_es="Virrey", name_en="Virrey")
    return PropertyFactory(
        district=district,
        slug="duplex-virrey",
        title_es="Dúplex en Parque Virrey",
        title_en="Duplex in Parque Virrey",
        address="Calle 88 # 15-23",
        max_guests=3,
        price_per_night=Decimal("100.00"),
        cleaning_fee=Decimal("20.00"),
        latitude=Decimal("4.672"),
        longitude=Decimal("-74.054"),
    )
