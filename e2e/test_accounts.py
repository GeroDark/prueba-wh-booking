"""Accounts in a real browser: forgotten password, from the login page to signed in again."""

import re

import pytest
from django.contrib.auth import get_user_model
from playwright.sync_api import expect

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]

User = get_user_model()


def test_forgotten_password(page, live_server, mailoutbox):
    User.objects.create_user("ana@mail.com", "Luna-Mar-Cielo-7", full_name="Ana Torres")

    page.goto(f"{live_server.url}/es/accounts/login/")
    page.click("text=¿Olvidaste tu contraseña?")
    page.fill("#id_email", "Ana@Mail.com")
    page.click(".auth__submit")  # not the header's language buttons
    expect(page.locator("h1")).to_have_text("Revisa tu correo")

    path = re.search(r"https?://[^/\s]+(/\S+/password/reset/\S+/)", mailoutbox[0].body).group(1)
    page.goto(f"{live_server.url}{path}")
    expect(page.locator("h1")).to_have_text("Crea una nueva contraseña")

    # The checklist blocks a password with personal data before it reaches the server.
    page.fill("#id_password", "AnaTorres-2026")
    page.click(".auth__submit")
    expect(page.locator("h1")).to_have_text("Crea una nueva contraseña")
    expect(page.locator("[data-rule=personal]")).not_to_have_class(re.compile("is-valid"))

    page.fill("#id_password", "Brisa-Puerto-Faro-9")
    page.click(".auth__submit")

    expect(page).to_have_url(f"{live_server.url}/es/")
    expect(page.locator("body")).to_contain_text("Tu contraseña se actualizó")
    assert User.objects.get().check_password("Brisa-Puerto-Faro-9")

    page.goto(f"{live_server.url}{path}")  # the link worked once
    expect(page.locator("h1")).to_have_text("Este enlace ya no es válido")
