import re

import pytest
from django.conf import settings
from django.db import DatabaseError

from apps.core import views

# Pages read their content (home, menus, footer) from the database.
pytestmark = pytest.mark.django_db


def test_root_redirects_to_default_language(client):
    response = client.get("/")

    assert response.status_code == 302
    assert response["Location"] == "/es/"


@pytest.mark.parametrize("language", ["es", "en"])
def test_home_renders_in_each_language(client, language):
    response = client.get(f"/{language}/")

    assert response.status_code == 200
    assert f'<html lang="{language}">' in response.text


def test_interface_strings_are_translated(client):
    assert "Saltar al contenido" in client.get("/es/").text
    assert "Skip to content" in client.get("/en/").text


def test_language_switch_redirects_to_the_same_page_in_the_new_language(client):
    response = client.post("/i18n/setlang/", {"language": "en", "next": "/es/"})

    assert response.status_code == 302
    assert response["Location"] == "/en/"
    assert response.cookies[settings.LANGUAGE_COOKIE_NAME].value == "en"


@pytest.mark.parametrize(
    ("page", "browser_language", "target", "expected"),
    [
        ("/en/", "es", "es", "/es/"),
        ("/es/", "en", "en", "/en/"),
        ("/en/?city=bogota", "es", "es", "/es/?city=bogota"),
    ],
)
def test_switching_language_works_when_browser_language_differs_from_the_page(
    client, page, browser_language, target, expected
):
    """Regression: with no language cookie, set_language could not translate `next`
    when the browser's Accept-Language differed from the page prefix."""
    html = client.get(page, HTTP_ACCEPT_LANGUAGE=browser_language).text
    forms = re.findall(r'name="next" value="([^"]+)">\s*<button[^>]*value="(\w+)"', html)
    next_url = dict((language, url) for url, language in forms)[target]

    response = client.post(
        "/i18n/setlang/",
        {"language": target, "next": next_url},
        HTTP_ACCEPT_LANGUAGE=browser_language,
    )

    assert response["Location"] == expected


def test_language_switcher_marks_the_active_language(client):
    html = client.get("/en/").text

    assert re.search(r'value="en"[^>]*class="lang-switch__option is-active"', html)
    assert not re.search(r'value="es"[^>]*class="lang-switch__option is-active"', html)


@pytest.mark.django_db
def test_health_check_reports_ok_without_touching_the_database(client, django_assert_num_queries):
    """Called every few seconds: a query here would keep the free database awake (D39)."""
    with django_assert_num_queries(0):
        response = client.get("/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_database_health_check_reports_ok(client):
    response = client.get("/health/db/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_database_health_check_reports_database_failure(client, monkeypatch):
    class BrokenConnection:
        def cursor(self):
            raise DatabaseError("connection refused")

    monkeypatch.setattr(views, "connection", BrokenConnection())

    response = client.get("/health/db/")

    assert response.status_code == 503
    assert response.json()["status"] == "error"
