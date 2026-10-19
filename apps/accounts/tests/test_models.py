from datetime import date

import pytest
from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import translation

pytestmark = pytest.mark.django_db

User = get_user_model()
PASSWORD = "Wynw00d-Stay"


def test_create_user_normalizes_the_whole_email():
    user = User.objects.create_user("  Ana@Mail.COM ", PASSWORD)

    assert user.email == "ana@mail.com"
    assert user.check_password(PASSWORD)
    assert not user.is_staff
    assert not user.is_superuser


def test_create_user_requires_an_email():
    with pytest.raises(ValueError):
        User.objects.create_user("", PASSWORD)


def test_create_superuser_sets_admin_flags():
    admin = User.objects.create_superuser("admin@wh.com", PASSWORD)

    assert admin.is_staff
    assert admin.is_superuser


def test_database_rejects_duplicate_email_with_different_case():
    User.objects.create_user("ana@mail.com", PASSWORD)

    # bulk_create skips save(), so this reaches the case-insensitive constraint directly.
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.bulk_create([User(email="ANA@mail.com")])


@pytest.mark.parametrize(
    ("language", "message"),
    [
        ("en", "An account with this email already exists."),
        ("es", "Ya existe una cuenta con este correo electrónico."),
    ],
)
def test_constraint_validation_reports_duplicate_email(language, message):
    User.objects.create_user("ana@mail.com", PASSWORD)

    with translation.override(language), pytest.raises(ValidationError, match=message):
        User(email="Ana@Mail.com").validate_constraints()


def test_login_with_email_is_case_insensitive(rf):
    user = User.objects.create_user("ana@mail.com", PASSWORD)

    # With a request, as the login form does: the failed-attempt limit needs it (D41).
    assert (
        authenticate(rf.post("/es/accounts/login/"), email="ANA@MAIL.COM", password=PASSWORD)
        == user
    )


@pytest.mark.parametrize(
    ("full_name", "expected_full", "expected_short"),
    [
        ("Ana María Torres", "Ana María Torres", "Ana"),
        ("", "ana@mail.com", "ana@mail.com"),
    ],
)
def test_display_names_fall_back_to_email(full_name, expected_full, expected_short):
    user = User(email="ana@mail.com", full_name=full_name)

    assert user.get_full_name() == expected_full
    assert user.get_short_name() == expected_short


def test_admin_edits_get_the_same_phone_and_birth_date_rules():
    user = User(email="ana@mail.com", full_name="Ana Torres", phone_prefix="+5151")
    user.phone_number, user.birth_date = "abc", date(2099, 1, 1)

    with pytest.raises(ValidationError) as error:
        user.full_clean(exclude=["password"])

    assert {"phone_number", "birth_date"} <= error.value.message_dict.keys()


def test_admin_phone_is_stored_normalized():
    user = User(email="ana@mail.com", phone_prefix="+51", phone_number="987 654-321")

    user.full_clean(exclude=["password"])

    assert (user.phone_prefix, user.phone_number) == ("+51", "987654321")
