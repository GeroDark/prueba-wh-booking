"""Abuse limits (D41): failed sign-ins per account + network, and holds per network."""

from datetime import timedelta
from decimal import Decimal

import pytest
import time_machine
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client
from django.utils import timezone

from apps.bookings.models import Booking
from apps.bookings.services import hold_dates
from apps.core.ip import client_ip, hashed_client_ip
from apps.properties.tests.factories import PropertyFactory

pytestmark = pytest.mark.django_db

User = get_user_model()
PASSWORD = "Luna-Mar-Cielo-7"
LOGIN = "/es/accounts/login/"


def attempt(client, password, email="ana@mail.com"):
    return client.post(LOGIN, {"username": email, "password": password})


# Failed sign-ins


def test_five_failures_pause_that_account_from_that_network(client):
    User.objects.create_user("ana@mail.com", PASSWORD)
    for _ in range(4):
        assert attempt(client, "wrong-password-1").status_code == 200
    assert attempt(client, "wrong-password-1").status_code == 429  # the fifth one locks

    response = attempt(client, PASSWORD)  # even the right password is refused now

    assert response.status_code == 429
    assert "Demasiados intentos" in response.text
    assert "_auth_user_id" not in client.session


def test_changing_the_letter_case_does_not_get_new_attempts(client):
    """Found while testing: "ANA@mail.com" counted as another account."""
    User.objects.create_user("ana@mail.com", PASSWORD)
    for spelling in (
        "ana@mail.com",
        "ANA@mail.com",
        "Ana@Mail.com",
        " ana@MAIL.com",
        "aNa@mail.com",
    ):
        attempt(client, "wrong-password-1", email=spelling)

    assert attempt(client, PASSWORD, email="AnA@mail.com").status_code == 429


def test_the_pause_ends_after_15_minutes(client):
    User.objects.create_user("ana@mail.com", PASSWORD)
    for _ in range(5):
        attempt(client, "wrong-password-1")

    with time_machine.travel(timezone.now() + timedelta(minutes=16)):
        response = attempt(client, PASSWORD)

    assert response.status_code == 302


def test_another_network_can_still_sign_in_to_the_same_account():
    """Locking by account + network: an attacker cannot lock a guest out of their account."""
    User.objects.create_user("ana@mail.com", PASSWORD)
    attacker = Client(REMOTE_ADDR="203.0.113.7")
    for _ in range(6):
        attempt(attacker, "wrong-password-1")

    guest = Client(REMOTE_ADDR="198.51.100.20")

    assert attempt(guest, PASSWORD).status_code == 302


def test_a_successful_sign_in_resets_the_count(client):
    User.objects.create_user("ana@mail.com", PASSWORD)
    for _ in range(4):
        attempt(client, "wrong-password-1")
    assert attempt(client, PASSWORD).status_code == 302
    client.post("/es/accounts/logout/")

    for _ in range(4):
        attempt(client, "wrong-password-1")

    assert attempt(client, PASSWORD).status_code == 302


def test_unknown_accounts_get_the_same_pause(client):
    """The lockout page appears for any e-mail, so it does not reveal which accounts exist."""
    for _ in range(5):
        attempt(client, "wrong-password-1", email="nobody@mail.com")

    assert attempt(client, "wrong-password-1", email="nobody@mail.com").status_code == 429


# The visitor's IP behind the proxy


def test_client_ip_uses_the_proxy_header_and_ignores_forged_ones(rf, settings):
    settings.CLIENT_IP_HEADER = "HTTP_CF_CONNECTING_IP"
    request = rf.get(
        "/",
        REMOTE_ADDR="10.0.0.1",  # the proxy
        HTTP_CF_CONNECTING_IP="198.51.100.20",  # set by Cloudflare
        HTTP_X_FORWARDED_FOR="1.2.3.4",  # anyone can send this one
    )

    assert client_ip(request) == "198.51.100.20"


def test_client_ip_without_a_proxy_or_with_garbage(rf, settings):
    settings.CLIENT_IP_HEADER = ""
    assert client_ip(rf.get("/", REMOTE_ADDR="198.51.100.20")) == "198.51.100.20"

    settings.CLIENT_IP_HEADER = "HTTP_CF_CONNECTING_IP"
    forged = rf.get("/", REMOTE_ADDR="10.0.0.1", HTTP_CF_CONNECTING_IP="<script>")
    assert client_ip(forged) == "10.0.0.1"


def test_the_ip_is_stored_only_as_a_keyed_hash(rf):
    hashed = hashed_client_ip(rf.get("/", REMOTE_ADDR="198.51.100.20"))

    assert len(hashed) == 32 and "198.51" not in hashed
    assert hashed == hashed_client_ip(rf.get("/", REMOTE_ADDR="198.51.100.20"))
    assert hashed != hashed_client_ip(rf.get("/", REMOTE_ADDR="198.51.100.21"))


# Holds per network


def days(n):
    return timezone.localdate() + timedelta(days=n)


def test_one_network_cannot_hold_more_than_the_limit(settings):
    settings.BOOKING_MAX_HOLDS_PER_IP = 3
    props = PropertyFactory.create_batch(4, max_guests=2, price_per_night=Decimal("100"))
    for prop in props[:3]:
        hold_dates(prop=prop, check_in=days(5), check_out=days(7), guests=1, client_ip_hash="net-a")

    with pytest.raises(ValidationError) as error:
        hold_dates(
            prop=props[3], check_in=days(5), check_out=days(7), guests=1, client_ip_hash="net-a"
        )

    assert error.value.code == "too_many_holds"
    # Another network is not affected.
    hold_dates(prop=props[3], check_in=days(5), check_out=days(7), guests=1, client_ip_hash="net-b")


def test_expired_or_paid_holds_do_not_count(settings):
    settings.BOOKING_MAX_HOLDS_PER_IP = 1
    first, second = PropertyFactory.create_batch(2, max_guests=2)
    hold_dates(prop=first, check_in=days(5), check_out=days(7), guests=1, client_ip_hash="net-a")

    with time_machine.travel(timezone.now() + timedelta(minutes=16)):  # the hold expired
        hold_dates(
            prop=second, check_in=days(5), check_out=days(7), guests=1, client_ip_hash="net-a"
        )


def test_many_sessions_from_one_network_hit_the_limit_through_the_site(settings):
    """The reviewer's case: several independent sessions, each holding dates."""
    settings.BOOKING_MAX_HOLDS_PER_IP = 2
    props = PropertyFactory.create_batch(3, max_guests=2)

    statuses = []
    for prop in props:
        session = Client(REMOTE_ADDR="203.0.113.7")  # a new session each time
        response = session.post(
            f"/es/properties/{prop.slug}/",
            {"check_in": days(5), "check_out": days(7), "guests": 1},
        )
        statuses.append(response.status_code)

    assert statuses == [302, 302, 200]  # the third one stays on the page with the message
    assert Booking.objects.filter(status=Booking.Status.PENDING).count() == 2
    assert "varias reservas en curso" in response.text
