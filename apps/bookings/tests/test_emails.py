"""Confirmation e-mail (requirement 7, D37): once, after the payment, in the booking's language."""

import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import transaction
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.bookings.emails import send_booking_confirmation
from apps.bookings.models import Booking, BookingLine
from apps.core.models import SiteSettings, SocialLink
from apps.payments.cards import VISA, Card
from apps.payments.services import pay_booking
from apps.properties.tests.factories import (
    CountryFactory,
    PropertyFactory,
    PropertyImageFactory,
    image_upload,
)

from .factories import BookingFactory

pytestmark = pytest.mark.django_db

User = get_user_model()
APPROVED = Card("4242424242424242", 12, 2030, "123", VISA)
DECLINED = Card("4000000000000002", 12, 2030, "123", VISA)


@pytest.fixture
def booking():
    site = SiteSettings.load()
    site.whatsapp_number = "+51 947 022 549"
    site.cancellation_policy_url = "https://example.com/cancellation"
    site.save()
    SocialLink.objects.create(network="instagram", url="https://instagram.com/wynwood.house")
    prop = PropertyFactory(address="Calle Alcanfores 1262")
    PropertyImageFactory(property=prop)
    # Another country: the one of the booked property is not suggested again.
    CountryFactory(code="pe", name_es="Perú", name_en="Peru", image=image_upload())
    guest = User.objects.create_user("ana@mail.com", "Luna-Mar-Cielo-7", full_name="Ana Torres")
    booking = BookingFactory(
        property=prop,
        guest=guest,
        status=Booking.Status.PENDING,
        expires_at=timezone.now() + timedelta(minutes=15),
        total=Decimal("320.11"),
        language="es",
    )
    BookingLine.objects.create(
        booking=booking,
        kind=BookingLine.Kind.CLEANING,
        label_es="Tarifa de limpieza",
        label_en="Cleaning fee",
        amount=Decimal("20.00"),
    )
    return booking


def pay(booking, card=APPROVED):
    return pay_booking(booking=booking, card=card, idempotency_key=uuid.uuid4())


@override_settings(SITE_URL="https://wh.example.com")
def test_paying_sends_one_confirmation_in_the_booking_language(
    booking, mailoutbox, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        pay(booking)

    assert len(mailoutbox) == 1
    message = mailoutbox[0]
    html = message.alternatives[0][0]
    assert message.to == ["ana@mail.com"]
    assert message.subject == f"Tu reserva {booking.reference} está confirmada"
    assert "¡Hola, Ana!" in html and "Tarifa de limpieza" in html
    assert "Calle Alcanfores 1262" in html  # the exact address goes only to the guest
    assert "US$ 320,11" in html
    assert f"https://wh.example.com/es/bookings/{booking.reference}/" in html
    assert "https://wa.me/51947022549?text=" in html and booking.reference in html
    assert "https://wh.example.com/static/img/email/instagram.png" in html
    booking.refresh_from_db()
    assert booking.confirmation_sent_at is not None


def test_the_email_uses_jpeg_copies_of_the_webp_photos(
    booking, mailoutbox, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        pay(booking)

    html = mailoutbox[0].alternatives[0][0]
    assert ".webp" not in html  # about a quarter of e-mail clients cannot show WebP
    assert html.count(".jpg") >= 2  # the property photo and the other destination


def test_an_english_booking_gets_the_english_email(
    booking, mailoutbox, django_capture_on_commit_callbacks
):
    Booking.objects.filter(pk=booking.pk).update(language="en")
    booking.refresh_from_db()

    with django_capture_on_commit_callbacks(execute=True):
        pay(booking)

    message = mailoutbox[0]
    assert message.subject == f"Your booking {booking.reference} is confirmed"
    assert "Cleaning fee" in message.alternatives[0][0]
    assert "/en/bookings/" in message.body


def test_the_plain_text_version_has_the_essentials(
    booking, mailoutbox, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        pay(booking)

    text = mailoutbox[0].body
    assert "<" not in text
    assert booking.reference in text and "Total: US$ 320,11" in text


def test_a_declined_payment_sends_nothing(booking, mailoutbox, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        pay(booking, DECLINED)

    assert mailoutbox == []


def test_nothing_is_sent_if_the_payment_is_rolled_back(booking, mailoutbox):
    with pytest.raises(RuntimeError), transaction.atomic():
        pay(booking)
        raise RuntimeError("something failed after the charge")

    assert mailoutbox == []


def test_the_email_is_never_sent_twice(booking, mailoutbox, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        pay(booking)
        pay(booking)  # same booking paid again from another tab: no new charge, no new e-mail

    assert send_booking_confirmation(booking.pk) is False
    assert len(mailoutbox) == 1


def test_a_failed_send_does_not_undo_the_payment_and_is_retried(
    booking, mailoutbox, django_capture_on_commit_callbacks, monkeypatch, caplog
):
    def broken_send(self, fail_silently=False):
        raise ConnectionError("provider down")

    with monkeypatch.context() as patch:
        patch.setattr("django.core.mail.EmailMultiAlternatives.send", broken_send)
        with django_capture_on_commit_callbacks(execute=True):
            pay(booking)

    booking.refresh_from_db()
    assert booking.status == Booking.Status.CONFIRMED
    assert booking.confirmation_sent_at is None
    assert "could not be sent" in caplog.text

    call_command("send_booking_confirmations")

    booking.refresh_from_db()
    assert len(mailoutbox) == 1
    assert booking.confirmation_sent_at is not None


def test_pending_bookings_are_never_emailed(booking, mailoutbox):
    assert send_booking_confirmation(booking.pk) is False
    call_command("send_booking_confirmations")

    assert mailoutbox == []


def test_admin_can_resend_the_confirmation(
    booking, admin_client, mailoutbox, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        pay(booking)

    response = admin_client.post(
        reverse("admin:bookings_booking_changelist"),
        {"action": "resend_confirmation", "_selected_action": [booking.pk]},
        follow=True,
    )

    assert response.status_code == 200
    assert len(mailoutbox) == 2


def test_the_country_of_the_stay_is_not_suggested_again(
    booking, mailoutbox, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        pay(booking)

    html = mailoutbox[0].alternatives[0][0]
    assert "?country=country-pe" in html
    assert "?country=country-co" not in html
