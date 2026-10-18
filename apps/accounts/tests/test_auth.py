from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.bookings.models import Booking
from apps.properties.tests.factories import PropertyFactory

pytestmark = pytest.mark.django_db

User = get_user_model()
GOOD_PASSWORD = "Wynwood-Stay-2026"
SIGNUP, LOGIN, LOGOUT = "/es/accounts/signup/", "/es/accounts/login/", "/es/accounts/logout/"


def signup(client, **overrides):
    data = {"email": "ana@mail.com", "full_name": "Ana Torres", "password": GOOD_PASSWORD}
    data.update(overrides)
    return client.post(SIGNUP, data)


# Sign up


def test_signup_creates_the_account_and_signs_in(client):
    response = signup(client, email="  Ana@Mail.com ")

    user = User.objects.get()
    assert response.status_code == 302
    assert response["Location"] == "/es/"
    assert user.email == "ana@mail.com"
    assert user.check_password(GOOD_PASSWORD)
    assert user.preferred_language == "es"
    assert client.get("/es/").context["user"] == user


def test_signup_rejects_an_email_already_registered_in_any_case(client):
    User.objects.create_user("ana@mail.com", GOOD_PASSWORD)

    response = signup(client, email="ANA@mail.com")

    assert response.status_code == 200
    assert "Ya existe una cuenta con este correo. Inicia sesión." in response.text
    assert User.objects.count() == 1


@pytest.mark.parametrize(
    ("password", "message"),
    [
        ("Ab1-", "al menos 8 caracteres"),  # Django's MinimumLengthValidator
        ("12345678", "completamente numérica"),  # NumericPasswordValidator
        ("password123", "demasiado común"),  # CommonPasswordValidator
        ("SoloLetrasLargas", "al menos un número o un símbolo"),  # ours
        ("torres-2026!", "no puede contener tu nombre ni tu correo"),  # ours
        ("x-ana2026!", "no puede contener tu nombre ni tu correo"),  # e-mail name part
    ],
)
def test_signup_requires_a_secure_password(client, password, message):
    response = signup(client, password=password)

    assert response.status_code == 200
    assert message in response.text.lower()
    assert not User.objects.exists()


def test_signup_with_the_data_of_the_bug_report_explains_every_problem(client):
    """ "prueba@gma" / a name with digits / a password made of the e-mail's name part."""
    response = signup(
        client, email="prueba@gma", full_name="asdfsd dasf ds 65186", password="prueba48621"
    )

    form = response.context["form"]
    assert "nombre@ejemplo.com" in form.errors["email"][0]
    assert form.errors["full_name"] == ["Usa solo letras, espacios, guiones o apóstrofos."]
    # Checked against the typed e-mail although the e-mail itself is invalid, with one
    # message per problem (personal data, common word).
    assert form.errors["password"] == [
        "La contraseña no puede contener tu nombre ni tu correo electrónico.",
        "Esta contraseña es una palabra común con números o símbolos. "
        "Elige una más difícil de adivinar.",
    ]
    assert "Introduzca" not in response.text  # Django's "usted" messages are replaced
    assert not User.objects.exists()


def test_signup_says_what_is_missing_in_each_empty_field(client):
    form = signup(client, email="", full_name="   ", password="").context["form"]

    assert form.errors["email"] == ["Ingresa tu correo electrónico."]
    assert form.errors["full_name"] == ["Ingresa tu nombre y apellido."]
    assert form.errors["password"] == ["Crea una contraseña."]


@pytest.mark.parametrize(
    "email",
    [
        "prueba@gma",
        "prueba@",
        "@gmail.com",
        "pru eba@gmail.com",
        "prueba@@gmail.com",
        "prueba@gmail..com",
        f"{'a' * 250}@mail.com",  # longer than the 254 characters an address can have
    ],
)
def test_signup_rejects_invalid_emails(client, email):
    response = signup(client, email=email)

    assert "email" in response.context["form"].errors
    assert not User.objects.exists()


@pytest.mark.parametrize("name", ["Ana", "Ana 2", "Ana <script>", "Ana_Torres"])
def test_signup_rejects_names_that_are_not_a_first_and_last_name(client, name):
    response = signup(client, full_name=name)

    assert "full_name" in response.context["form"].errors
    assert not User.objects.exists()


def test_signup_saves_the_name_tidied_up(client):
    # "Jose" + combining accent: some keyboards send é as two characters.
    signup(client, full_name="  María   Jose\u0301  O'Connor ", password=GOOD_PASSWORD)

    assert User.objects.get().full_name == "María José O'Connor"


@pytest.mark.parametrize("password", ["contraseña123", "Password2026!"])
def test_signup_rejects_common_words_with_numbers(client, password):
    response = signup(client, password=password)

    assert "palabra común" in " ".join(response.context["form"].errors["password"])


def test_signup_fields_carry_the_messages_for_the_live_hints(client):
    html = client.get(SIGNUP).text

    assert 'data-error-required="Ingresa tu correo electrónico."' in html
    assert 'data-error-invalid="Ingresa un correo electrónico válido' in html
    assert 'data-error-invalid="Ingresa tu nombre y apellido usando solo letras."' in html
    assert "data-validate" in html


def test_signup_marks_invalid_fields_for_screen_readers(client):
    html = signup(client, email="not-an-email").text

    assert 'aria-invalid="true"' in html
    assert 'aria-describedby="id_email-error"' in html


def test_signup_follows_a_safe_next_url(client):
    response = client.post(
        f"{SIGNUP}?next=/es/search/",
        {
            "email": "ana@mail.com",
            "full_name": "Ana Torres",
            "password": GOOD_PASSWORD,
            "next": "/es/search/",
        },
    )

    assert response["Location"] == "/es/search/"


def test_signup_ignores_an_external_next_url(client):
    response = client.post(
        SIGNUP,
        {
            "email": "ana@mail.com",
            "full_name": "Ana Torres",
            "password": GOOD_PASSWORD,
            "next": "https://evil.example/",
        },
    )

    assert response["Location"] == "/es/"


def test_signed_in_users_do_not_see_the_signup_form(client):
    client.force_login(User.objects.create_user("ana@mail.com", GOOD_PASSWORD))

    assert client.get(SIGNUP)["Location"] == "/es/"


# Sign in / sign out


def test_login_with_email_in_any_case(client):
    User.objects.create_user("ana@mail.com", GOOD_PASSWORD)

    response = client.post(LOGIN, {"username": "ANA@mail.com", "password": GOOD_PASSWORD})

    assert response.status_code == 302


def test_login_error_does_not_reveal_whether_the_account_exists(client):
    User.objects.create_user("ana@mail.com", GOOD_PASSWORD)

    wrong_password = client.post(LOGIN, {"username": "ana@mail.com", "password": "nope"}).text
    unknown_email = client.post(LOGIN, {"username": "nobody@mail.com", "password": "nope"}).text

    message = "El correo o la contraseña no son correctos."
    assert message in wrong_password
    assert message in unknown_email


def test_logout_requires_post(client):
    client.force_login(User.objects.create_user("ana@mail.com", GOOD_PASSWORD))

    assert client.get(LOGOUT).status_code == 405
    assert client.post(LOGOUT).status_code == 302
    assert not client.get("/es/").context["user"].is_authenticated


def test_header_shows_sign_in_or_the_guest_name(client):
    assert "Iniciar sesión" in client.get("/es/").text

    client.force_login(
        User.objects.create_user("ana@mail.com", GOOD_PASSWORD, full_name="Ana Torres")
    )
    html = client.get("/es/").text

    assert "Hola, Ana" in html
    assert "Cerrar sesión" in html


def test_a_hold_made_before_signing_up_still_belongs_to_the_visitor(client):
    """Django rotates the session key on login but keeps its data (D12)."""
    prop = PropertyFactory(max_guests=2)
    today = timezone.localdate()
    client.post(
        f"/es/properties/{prop.slug}/",
        {
            "check_in": today + timedelta(days=5),
            "check_out": today + timedelta(days=7),
            "guests": 1,
        },
    )
    booking = Booking.objects.get()

    signup(client)

    assert client.get(f"/es/checkout/{booking.reference}/").status_code == 200
