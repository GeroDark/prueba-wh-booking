"""Checkout end to end through the views (D12): sign-up or details, payment, confirmation."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
import time_machine
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.bookings.models import Booking
from apps.payments.models import Payment
from apps.properties.tests.factories import PropertyFactory, PropertyImageFactory

pytestmark = pytest.mark.django_db

User = get_user_model()
PASSWORD = "Luna-Mar-Cielo-7"
VISA_OK, VISA_DECLINED = "4242 4242 4242 4242", "4000 0000 0000 0002"


def days(n):
    return (timezone.localdate() + timedelta(days=n)).isoformat()


@pytest.fixture
def prop():
    prop = PropertyFactory(
        max_guests=3,
        price_per_night=Decimal("100.00"),
        address="Calle Alcanfores 1262",
        latitude=Decimal("-12.124567"),
        longitude=Decimal("-77.029123"),
    )
    PropertyImageFactory(property=prop)
    return prop


def hold(client, prop):
    client.post(
        f"/es/properties/{prop.slug}/",
        {"check_in": days(5), "check_out": days(8), "guests": 2},
    )
    return Booking.objects.latest("created_at")


def checkout_url(booking):
    return f"/es/checkout/{booking.reference}/"


def guest_data(**overrides):
    data = {
        "email": "walter@mail.com",
        "password": PASSWORD,
        "full_name": "Walter Quispe",
        "nationality": "PE",
        "phone_region": "PE",
        "phone_number": "987 654 321",
        "birth_date": "1995-03-14",
    }
    data.update(overrides)
    return data


def complete_guest(email="ana@mail.com", **overrides):
    details = {
        "full_name": "Ana Torres",
        "nationality": "CO",
        "phone_prefix": "+57",
        "phone_number": "3001234567",
        "birth_date": date(1990, 1, 1),
    }
    details.update(overrides)
    return User.objects.create_user(email, PASSWORD, **details)


def pay(client, booking, number=VISA_OK, key="9b2f6f5e-3c1a-4c55-9d7e-1f2a3b4c5d6e", **extra):
    data = {"card_number": number, "expiry": "12/30", "cvc": "123", "idempotency_key": key}
    data.update(extra)
    return client.post(checkout_url(booking), data)


# Step 1: a new visitor signs up inside the checkout


def test_a_new_visitor_sees_the_sign_up_with_personal_details(client, prop):
    html = client.get(checkout_url(hold(client, prop))).text

    for name in ("email", "password", "full_name", "nationality", "phone_region", "phone_number"):
        assert f'name="{name}"' in html
    assert "No deseo suscribirme al boletín" in html
    assert "Al seleccionar Continuar, aceptas" in html


def test_signing_up_creates_the_account_logs_in_and_claims_the_hold(client, prop):
    booking = hold(client, prop)

    response = client.post(checkout_url(booking), guest_data())

    user = User.objects.get()
    booking.refresh_from_db()
    assert response["Location"] == checkout_url(booking)
    assert booking.guest == user
    assert (user.phone_prefix, user.phone_number) == ("+51", "987654321")
    assert user.nationality.code == "PE"
    assert user.marketing_opt_in  # the design's checkbox is "I do NOT want" the newsletter
    assert "Información de pago" in client.get(checkout_url(booking)).text


def test_the_newsletter_opt_out_is_respected(client, prop):
    booking = hold(client, prop)

    client.post(checkout_url(booking), guest_data(no_newsletter="on"))

    assert not User.objects.get().marketing_opt_in


def test_a_number_typed_with_its_own_prefix_keeps_it(client, prop):
    booking = hold(client, prop)

    client.post(checkout_url(booking), guest_data(phone_number="+34 612 345 678"))

    user = User.objects.get()
    assert (user.phone_prefix, user.phone_number) == ("+34", "612345678")


@pytest.mark.parametrize(
    ("overrides", "field", "message"),
    [
        ({"phone_number": "98765432a"}, "phone_number", "Usa solo números"),
        ({"phone_number": "1-800-FLOWERS"}, "phone_number", "Usa solo números"),
        ({"phone_number": "12345"}, "phone_number", "válido para el país"),
        ({"phone_number": "612 345 678"}, "phone_number", "válido para el país"),  # Spanish in PE
        ({"phone_region": ""}, "phone_region", "Selecciona el indicativo"),
        ({"phone_region": "XX"}, "phone_region", "Elige una de las opciones"),
        ({"nationality": ""}, "nationality", "Selecciona tu nacionalidad"),
        ({"nationality": "ZZ"}, "nationality", "Elige una de las opciones"),
        ({"birth_date": ""}, "birth_date", "Ingresa tu fecha de nacimiento"),
        ({"birth_date": "31/02/1990"}, "birth_date", "Ingresa una fecha válida"),
        ({"birth_date": "2099-01-01"}, "birth_date", "anterior a hoy"),
        ({"birth_date": "1880-01-01"}, "birth_date", "Revisa el año"),
        ({"full_name": "Walter 2"}, "full_name", "solo letras"),
        ({"email": "walter@mail"}, "email", "correo electrónico válido"),
    ],
)
def test_invalid_personal_details_are_explained(client, prop, overrides, field, message):
    booking = hold(client, prop)

    response = client.post(checkout_url(booking), guest_data(**overrides))

    assert response.status_code == 200
    assert message in " ".join(response.context["form"].errors[field])
    assert not User.objects.exists()


# Noon in Lima: midnight UTC would still be the 17th in the site's time zone.
@time_machine.travel(datetime(2026, 10, 18, 12, tzinfo=ZoneInfo("America/Lima")))
def test_guests_must_be_adults(client, prop):
    booking = hold(client, prop)

    seventeen = client.post(checkout_url(booking), guest_data(birth_date="2008-10-19"))
    assert "al menos 18 años" in " ".join(seventeen.context["form"].errors["birth_date"])

    eighteen_today = client.post(checkout_url(booking), guest_data(birth_date="2008-10-18"))
    assert eighteen_today.status_code == 302, eighteen_today.context["form"].errors


def test_an_existing_email_is_sent_to_sign_in(client, prop):
    complete_guest(email="walter@mail.com")
    booking = hold(client, prop)

    response = client.post(checkout_url(booking), guest_data(email="Walter@Mail.com"))

    assert "Ya existe una cuenta con este correo" in response.text
    assert f"/es/accounts/login/?next=/es/checkout/{booking.reference}/" in response.text


def test_signing_in_from_the_checkout_comes_back_to_it(client, prop):
    complete_guest()
    booking = hold(client, prop)

    response = client.post(
        f"/es/accounts/login/?next={checkout_url(booking)}",
        {"username": "ana@mail.com", "password": PASSWORD, "next": checkout_url(booking)},
    )

    assert response["Location"] == checkout_url(booking)
    assert "Información de pago" in client.get(checkout_url(booking)).text
    booking.refresh_from_db()
    assert booking.guest.email == "ana@mail.com"


def test_a_signed_in_guest_with_missing_details_completes_them(client, prop):
    user = User.objects.create_user("ana@mail.com", PASSWORD, full_name="Ana Torres")
    client.force_login(user)
    booking = hold(client, prop)

    page = client.get(checkout_url(booking)).text
    assert 'name="password"' not in page and 'name="phone_number"' in page

    response = client.post(
        checkout_url(booking),
        {
            "full_name": "Ana Torres",
            "nationality": "CO",
            "phone_region": "CO",
            "phone_number": "300 123 4567",
            "birth_date": "1990-01-01",
        },
    )

    user.refresh_from_db()
    assert response["Location"] == checkout_url(booking)
    assert user.has_guest_details and user.phone == "+57 3001234567"


def test_a_signed_in_guest_with_complete_details_goes_straight_to_payment(client, prop):
    client.force_login(complete_guest())

    html = client.get(checkout_url(hold(client, prop))).text

    assert "Información de pago" in html
    assert "4242 4242 4242 4242" in html  # test cards of the simulated gateway


# Step 2: payment


def test_an_approved_payment_confirms_and_shows_the_confirmation(client, prop):
    client.force_login(complete_guest())
    booking = hold(client, prop)

    response = pay(client, booking)

    booking.refresh_from_db()
    assert response["Location"] == f"/es/bookings/{booking.reference}/"
    assert booking.status == Booking.Status.CONFIRMED
    html = client.get(response["Location"]).text
    assert f"Reserva {booking.reference} confirmada" in html
    assert "Calle Alcanfores 1262" in html  # exact address, only after paying
    assert "google.com/maps/search/?api=1&amp;query=-12.124567%2C-77.029123" in html
    assert "Pagado con Visa terminada en 4242" in html


def test_a_declined_card_explains_why_and_offers_a_new_attempt(client, prop):
    client.force_login(complete_guest())
    booking = hold(client, prop)

    response = pay(client, booking, number=VISA_DECLINED)

    booking.refresh_from_db()
    assert "Tu tarjeta fue rechazada" in response.text
    assert booking.status == Booking.Status.PENDING
    new_key = response.context["form"]["idempotency_key"].value()
    assert str(new_key) != "9b2f6f5e-3c1a-4c55-9d7e-1f2a3b4c5d6e"  # a retry is a new attempt
    assert "4000 0000 0000 0002" not in response.text.split("test-cards")[0]  # not echoed


def test_sending_the_same_payment_form_twice_charges_once(client, prop):
    client.force_login(complete_guest())
    booking = hold(client, prop)

    first = pay(client, booking)
    second = pay(client, booking)  # e.g. the browser resends after a network error

    assert first["Location"] == second["Location"] == f"/es/bookings/{booking.reference}/"
    assert Payment.objects.filter(status=Payment.Status.SUCCEEDED).count() == 1


def test_a_hold_that_expires_before_paying_is_not_charged(client, prop):
    client.force_login(complete_guest())
    booking = hold(client, prop)

    with time_machine.travel(timezone.now() + timedelta(minutes=16)):
        response = pay(client, booking)

    assert response["Location"].startswith(f"/es/properties/{prop.slug}/?check_in=")
    assert not Payment.objects.exists()


def test_invalid_card_data_is_not_sent_to_the_gateway(client, prop):
    client.force_login(complete_guest())
    booking = hold(client, prop)

    response = pay(client, booking, number="4242 4242 4242 4241", cvc="987")

    assert "no es válido" in response.text
    assert 'value="987"' not in response.text  # the security code is never written back
    assert not Payment.objects.exists()


def test_checkout_pages_are_never_cached(client, prop):
    response = client.get(checkout_url(hold(client, prop)))

    assert "no-store" in response["Cache-Control"]


# Confirmation and ownership


def test_a_paid_checkout_opens_the_confirmation(client, prop):
    client.force_login(complete_guest())
    booking = hold(client, prop)
    pay(client, booking)

    assert client.get(checkout_url(booking))["Location"] == f"/es/bookings/{booking.reference}/"


def test_an_unpaid_booking_has_no_confirmation_yet(client, prop):
    client.force_login(complete_guest())
    booking = hold(client, prop)

    assert client.get(f"/es/bookings/{booking.reference}/")["Location"] == checkout_url(booking)


def test_other_people_get_a_404_on_checkout_and_confirmation(client, prop, django_user_model):
    client.force_login(complete_guest())
    booking = hold(client, prop)
    pay(client, booking)
    stranger = django_user_model.objects.create_user("eve@mail.com", PASSWORD)

    client.logout()
    assert client.get(f"/es/bookings/{booking.reference}/").status_code == 404
    client.force_login(stranger)
    assert client.get(f"/es/bookings/{booking.reference}/").status_code == 404
    assert client.get(checkout_url(booking)).status_code == 404


def test_an_idempotency_key_of_another_booking_is_refused(client, prop):
    client.force_login(complete_guest())
    first = hold(client, prop)
    pay(client, first, number=VISA_DECLINED)
    other_prop = PropertyFactory(max_guests=3)
    second = hold(client, other_prop)

    response = pay(client, second)  # same key as the first booking's payment

    assert response.status_code == 400
    assert not second.payments.exists()
