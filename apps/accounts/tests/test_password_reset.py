"""Password reset (D43): a one-hour, single-use link by e-mail, without revealing who has an
account, without letting anyone flood an inbox, and without trusting the Host header."""

import re
from datetime import timedelta

import pytest
import time_machine
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

pytestmark = pytest.mark.django_db

User = get_user_model()
OLD, NEW = "Luna-Mar-Cielo-7", "Brisa-Puerto-Faro-9"
RESET, SENT, LOGIN = (
    "/es/accounts/password/reset/",
    "/es/accounts/password/reset/sent/",
    "/es/accounts/login/",
)


@pytest.fixture(autouse=True)
def _site_url(settings):
    settings.SITE_URL = "https://wh.example"


@pytest.fixture
def ana():
    return User.objects.create_user("ana@mail.com", OLD, full_name="Ana Torres")


def ask(client, email="ana@mail.com", prefix="/es"):
    return client.post(f"{prefix}/accounts/password/reset/", {"email": email})


def link_in(message):
    return re.search(r"https://wh\.example(/\S+/password/reset/\S+/)", message.body).group(1)


def open_link(client, path):
    """Django swaps the token in the URL for one in the session (so it cannot leak through the
    Referer header) and redirects to .../set-password/."""
    response = client.get(path)
    assert response.status_code == 302
    return response["Location"]


# Asking for the link


def test_the_link_arrives_in_the_language_of_the_page(client, ana, mailoutbox):
    response = ask(client)

    assert response.status_code == 302
    assert response["Location"] == SENT
    [message] = mailoutbox
    assert message.to == ["ana@mail.com"]
    assert message.subject == "Crea una nueva contraseña para Wynwood House"
    assert "¡Hola, Ana!" in message.body
    assert "60 minutos" in message.body
    assert link_in(message).startswith("/es/accounts/password/reset/")
    html = message.alternatives[0][0]
    assert f"https://wh.example{link_in(message)}" in html


def test_english_page_english_email(client, ana, mailoutbox):
    ask(client, prefix="/en")

    assert mailoutbox[0].subject == "Create a new password for Wynwood House"
    assert link_in(mailoutbox[0]).startswith("/en/accounts/password/reset/")


def test_the_page_does_not_reveal_whether_the_account_exists(client, ana, mailoutbox):
    known, unknown = ask(client), ask(Client(), email="nadie@mail.com")

    assert known.status_code == unknown.status_code == 302
    assert known["Location"] == unknown["Location"] == SENT
    assert len(mailoutbox) == 1
    assert "Si hay una cuenta con ese correo" in client.get(SENT).text


def test_the_email_is_found_in_any_letter_case(client, ana, mailoutbox):
    ask(client, email="  ANA@Mail.com ")

    assert mailoutbox[0].to == ["ana@mail.com"]


def test_inactive_accounts_get_nothing(client, ana, mailoutbox):
    User.objects.filter(pk=ana.pk).update(is_active=False)

    ask(client)

    assert mailoutbox == []


def test_one_email_per_account_every_five_minutes(client, ana, mailoutbox):
    """Otherwise anyone could fill a guest's inbox by submitting the form in a loop."""
    start = timezone.now()
    with time_machine.travel(start, tick=False):
        for _ in range(5):
            assert ask(client)["Location"] == SENT  # same answer every time
    assert len(mailoutbox) == 1

    with time_machine.travel(start + timedelta(minutes=5, seconds=1), tick=False):
        ask(client)
    assert len(mailoutbox) == 2


def test_the_link_ignores_a_forged_host_header(client, ana, mailoutbox, settings):
    """Password reset poisoning: with a link built from the Host header, an attacker asking for
    a reset with "Host: evil.example" would receive the victim's token when they click."""
    settings.ALLOWED_HOSTS = ["*"]

    client.post(RESET, {"email": "ana@mail.com"}, HTTP_HOST="evil.example")

    assert "evil.example" not in mailoutbox[0].body
    assert "evil.example" not in mailoutbox[0].alternatives[0][0]
    assert link_in(mailoutbox[0])


@pytest.mark.parametrize("email", ["", "ana@", "a" * 250 + "@mail.com"])
def test_invalid_emails_are_rejected_with_a_message(client, email, mailoutbox):
    response = ask(client, email=email)

    assert response.status_code == 200
    assert response.context["form"].errors["email"]
    assert mailoutbox == []


# Using the link


def test_the_link_sets_the_new_password_and_signs_in(client, ana, mailoutbox):
    ask(client)
    form_url = open_link(client, link_in(mailoutbox[0]))

    page = client.get(form_url)
    assert "Crea una nueva contraseña" in page.text
    response = client.post(form_url, {"password": NEW})

    assert response.status_code == 302
    assert response["Location"] == "/es/"
    ana.refresh_from_db()
    assert ana.check_password(NEW)
    assert not ana.check_password(OLD)
    assert client.session["_auth_user_id"] == str(ana.pk)
    assert "Tu contraseña se actualizó" in client.get("/es/").text


def test_the_link_works_once(client, ana, mailoutbox):
    ask(client)
    path = link_in(mailoutbox[0])
    client.post(open_link(client, path), {"password": NEW})

    response = Client().get(path)  # the token depended on the old password

    assert response.status_code == 200
    assert "Este enlace ya no es válido" in response.text


def test_the_link_expires_after_one_hour(client, ana, mailoutbox):
    start = timezone.now()
    with time_machine.travel(start, tick=False):
        ask(client)
    with time_machine.travel(start + timedelta(hours=1, minutes=1), tick=False):
        response = client.get(link_in(mailoutbox[0]))

    assert "Este enlace ya no es válido" in response.text


@pytest.mark.parametrize(
    "path",
    [
        "/es/accounts/password/reset/MQ/abc-123/",  # forged token
        "/es/accounts/password/reset/xx/abc-123/",  # garbage user id
        "/es/accounts/password/reset/OTk5OTk/abc-123/",  # user that does not exist
    ],
)
def test_forged_links_are_refused(client, ana, path):
    response = client.get(path)

    assert response.status_code == 200
    assert "Este enlace ya no es válido" in response.text


@pytest.mark.parametrize(
    "password",
    ["Ana-Torres-2026", "password123", "corta1"],  # personal data, common, too short
)
def test_weak_passwords_are_refused(client, ana, mailoutbox, password):
    ask(client)
    form_url = open_link(client, link_in(mailoutbox[0]))

    response = client.post(form_url, {"password": password})

    assert response.status_code == 200
    assert response.context["form"].errors["password"]
    ana.refresh_from_db()
    assert ana.check_password(OLD)


def test_other_sessions_are_closed(client, ana, mailoutbox):
    """A stolen session (someone signed in on another device) stops working."""
    elsewhere = Client()
    elsewhere.force_login(ana)
    assert elsewhere.get("/es/").context["user"].is_authenticated

    ask(client)
    client.post(open_link(client, link_in(mailoutbox[0])), {"password": NEW})

    assert not elsewhere.get("/es/").context["user"].is_authenticated


def test_the_reset_lifts_the_failed_sign_in_pause_on_every_network(ana, mailoutbox):
    """Locked out on the laptop, new password from the phone: the laptop can sign in again.
    (Signing in on the phone alone would only clear the phone's network.)"""
    laptop, phone = Client(REMOTE_ADDR="10.0.0.1"), Client(REMOTE_ADDR="10.0.0.2")
    for _ in range(5):
        laptop.post(LOGIN, {"username": "ana@mail.com", "password": "wrong-password-1"})
    assert laptop.post(LOGIN, {"username": "ana@mail.com", "password": OLD}).status_code == 429

    ask(phone)
    phone.post(open_link(phone, link_in(mailoutbox[0])), {"password": NEW})

    response = laptop.post(LOGIN, {"username": "ana@mail.com", "password": NEW})
    assert response.status_code == 302


def test_the_login_and_the_lockout_page_offer_the_reset(client, ana):
    assert RESET in client.get(LOGIN).text
    for _ in range(5):
        response = client.post(LOGIN, {"username": "ana@mail.com", "password": "wrong-password-1"})
    assert RESET in response.text
