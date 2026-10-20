"""End-to-end tests: a real browser (Playwright) against Django's live test server.

They check that templates, JavaScript (calendar, live quote, form hints) and the server work
together, which unit tests cannot. Run with `pytest -m e2e` after `python -m playwright install
chromium`; CI runs them in their own job.
"""

import os
from decimal import Decimal

import pytest
from django.test import override_settings

from apps.properties.tests.factories import (
    CityFactory,
    CountryFactory,
    DistrictFactory,
    PropertyFactory,
)

# Playwright's sync API runs an event loop in the test thread; the ORM calls made by the test
# itself (fixtures, assertions) are still plain synchronous code.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")


@pytest.fixture(scope="session", autouse=True)
def _plain_http_live_server():
    """The live server speaks plain HTTP. With DEBUG=false (as in CI) the production hardening
    would redirect the browser to https://localhost. The root conftest turns the redirect off
    per test, but the live server builds its middleware once, when it starts, and
    SecurityMiddleware reads the setting then: it has to be off before the server starts."""
    with override_settings(
        SECURE_SSL_REDIRECT=False,
        SESSION_COOKIE_SECURE=False,
        CSRF_COOKIE_SECURE=False,
    ):
        yield


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
