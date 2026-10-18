import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.accounts.validators import NumberOrSymbolValidator, PersonalInfoValidator


@pytest.mark.parametrize("password", ["casa-grande", "casagrande1", "casa grande", "casa_grande"])
def test_number_or_symbol_accepts(password):
    NumberOrSymbolValidator().validate(password)


def test_number_or_symbol_rejects_letters_only():
    with pytest.raises(ValidationError):
        NumberOrSymbolValidator().validate("CasaGrande")


@pytest.mark.parametrize(
    "password",
    ["Torres-2026", "mi-ANA.torres", "anatorres!99"],
)
def test_personal_info_rejects_name_or_email_parts(password):
    user = User(email="anatorres@mail.com", full_name="Ana Torres")

    with pytest.raises(ValidationError):
        PersonalInfoValidator().validate(password, user)


def test_personal_info_ignores_short_pieces_and_missing_user():
    user = User(email="al@mail.com", full_name="Al Bo")

    PersonalInfoValidator().validate("al-bo-2026-casa", user)  # pieces shorter than 3 letters
    PersonalInfoValidator().validate("anything", None)
