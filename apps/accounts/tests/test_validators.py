import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.accounts.validators import (
    CommonWordValidator,
    NumberOrSymbolValidator,
    PersonalInfoValidator,
    normalize_name,
    validate_full_name,
)


@pytest.mark.parametrize("password", ["casa-grande", "casagrande1", "casa grande", "casa_grande"])
def test_number_or_symbol_accepts(password):
    NumberOrSymbolValidator().validate(password)


@pytest.mark.parametrize("password", ["CasaGrande", "MontañaAzul", "CaféÁrbol"])
def test_number_or_symbol_rejects_letters_only(password):
    """ñ and accented vowels are letters, not symbols (the browser checklist agrees)."""
    with pytest.raises(ValidationError):
        NumberOrSymbolValidator().validate(password)


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


# Common words with numbers or symbols


@pytest.mark.parametrize(
    "password",
    [
        "contraseña123",
        "Contrasena2026!",
        "prueba48621",
        "password123!",
        "123Qwerty",
        "Wynwood2026#",
    ],
)
def test_common_word_rejects_a_common_word_with_numbers_or_symbols(password):
    with pytest.raises(ValidationError):
        CommonWordValidator().validate(password)


@pytest.mark.parametrize(
    "password",
    ["Wynwood-Stay-2026", "Q#8273645!", "luna-mar-cielo-7", "x9k2!pTq"],
)
def test_common_word_accepts_passwords_that_are_not_a_single_common_word(password):
    CommonWordValidator().validate(password)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("language", "example"), [("es", "Contraseña2026!"), ("en", "Password2026!")]
)
def test_the_checklist_warns_with_examples_the_server_really_rejects(client, language, example):
    """The browser cannot check common words, so the checklist says it up front. The example
    shown must be one the server rejects, or the hint would teach the wrong thing."""
    response = client.get(f"/{language}/accounts/signup/")

    assert f"“{example}”" in response.text
    with pytest.raises(ValidationError):
        CommonWordValidator().validate(example)


# Full name


@pytest.mark.parametrize(
    "name",
    [
        "Ana Torres",
        "José Ñúñez",
        "María-José O'Connor",
        "Zoë D’Angelo",
        "Nguyễn Văn An",
        "Jean-Luc St. John",
        "Ana de la Cruz",
        "Jose\u0301 Pe\u0301rez",  # decomposed accents (e + ´), as some keyboards send them
    ],
)
def test_full_name_accepts_real_names(name):
    validate_full_name(name)


@pytest.mark.parametrize(
    ("name", "code"),
    [
        ("asdfsd dasf ds 65186", "name_characters"),  # digits
        ("Ana Torres2", "name_characters"),
        ("Ana_Torres Ruiz", "name_characters"),
        ("Ana @Torres", "name_characters"),
        ("<b>Ana</b> Torres", "name_characters"),
        ("Ana Torres 😀", "name_characters"),
        ("Ana - Torres", "name_characters"),  # a lone hyphen is not a word
        ("Ana", "name_single_word"),
        ("  Ana  ", "name_single_word"),
    ],
)
def test_full_name_rejects_numbers_symbols_and_single_words(name, code):
    with pytest.raises(ValidationError) as error:
        validate_full_name(name)

    assert error.value.code == code


def test_normalize_name_composes_accents_and_collapses_spaces():
    assert normalize_name("  Jose\u0301   Pe\u0301rez ") == "José Pérez"


def test_personal_info_rejects_the_whole_email_even_with_a_short_name_part():
    """Covers what Django's similarity validator did before it was replaced (D05)."""
    with pytest.raises(ValidationError):
        PersonalInfoValidator().validate("Al@Mail.com-2026", User(email="al@mail.com"))
