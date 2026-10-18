import re

import pytest
from django.conf import settings
from django.db import DatabaseError

from apps.core import views


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


def test_language_switcher_marks_the_active_language(client):
    html = client.get("/en/").text

    assert re.search(r'value="en"[^>]*class="lang-switch__option is-active"', html)
    assert not re.search(r'value="es"[^>]*class="lang-switch__option is-active"', html)


@pytest.mark.django_db
def test_health_check_reports_ok(client):
    response = client.get("/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_check_reports_database_failure(client, monkeypatch):
    class BrokenConnection:
        def cursor(self):
            raise DatabaseError("connection refused")

    monkeypatch.setattr(views, "connection", BrokenConnection())

    response = client.get("/health/")

    assert response.status_code == 503
    assert response.json()["status"] == "error"
