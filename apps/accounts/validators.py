"""Validation of the guest's name and password (see D05 and D35).

Django already checks the length (8+), common passwords, numeric-only passwords and similarity
to the user's data. The password validators here add the remaining items of the Figma checklist
and catch common words dressed up with numbers ("contraseña123").
"""

import re
import string
import unicodedata
from functools import cache

from django.contrib.auth.password_validation import CommonPasswordValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

# One name word: letters (any alphabet) joined by an apostrophe, hyphen or period, as in
# O'Connor, Jean-Luc or St. John. [^\W\d_] is "a letter" in Python's Unicode regexes.
NAME_WORD = re.compile(r"[^\W\d_]+(?:['’.\-][^\W\d_]+)*\.?")


def normalize_name(value):
    """Compose accents (e + ´ -> é) and collapse repeated spaces."""
    return " ".join(unicodedata.normalize("NFC", value).split())


def validate_full_name(value):
    """First name and at least one surname, written with letters only.

    The name has to match the guest's ID at check-in, so numbers, symbols and single words are
    rejected. It cannot tell a real name from random letters; the ID check at the door does.
    """
    words = normalize_name(value).split(" ")
    if not all(NAME_WORD.fullmatch(word) for word in words):
        raise ValidationError(
            _("Use only letters, spaces, hyphens or apostrophes."), code="name_characters"
        )
    if len(words) < 2:
        raise ValidationError(_("Enter your first and last name."), code="name_single_word")


def strip_accents(value):
    return "".join(
        char for char in unicodedata.normalize("NFKD", value) if not unicodedata.combining(char)
    )


# Common in Spanish and missing from Django's English list.
SPANISH_COMMON_WORDS = frozenset(
    {"contrasena", "clave", "prueba", "secreto", "usuario", "bienvenido", "peru", "wynwood"}
)


@cache
def common_words():
    return frozenset(CommonPasswordValidator().passwords) | SPANISH_COMMON_WORDS


class CommonWordValidator:
    """A common word plus numbers or symbols at the ends ("contraseña123", "Password2026!").

    Django's CommonPasswordValidator only rejects exact matches of its list. Here the numbers and
    symbols around the word are removed and accents ignored before looking it up.
    """

    min_word_length = 4  # shorter "words" ("a", "qq") would reject random passwords

    def validate(self, password, user=None):
        word = strip_accents(password.lower()).strip(string.digits + string.punctuation + " ")
        if len(word) >= self.min_word_length and word in common_words():
            raise ValidationError(
                _(
                    "This password is a common word with numbers or symbols. "
                    "Choose one that is harder to guess."
                ),
                code="password_common_word",
            )

    def get_help_text(self):
        return _("Is not a common word with numbers or symbols.")


class NumberOrSymbolValidator:
    """At least one digit or one character that is not a letter."""

    def validate(self, password, user=None):
        if not re.search(r"[\d\W_]", password):
            raise ValidationError(
                _("The password must contain at least one number or symbol."),
                code="password_no_number_or_symbol",
            )

    def get_help_text(self):
        return _("Contains a number or symbol.")


class PersonalInfoValidator:
    """The password cannot contain the e-mail, its name part or any word of the full name.

    Used instead of Django's UserAttributeSimilarityValidator, which only compares the whole
    password with each attribute: this one also catches passwords that merely include them
    (e.g. "ana.torres2026" for ana.torres@mail.com).
    """

    min_length = 3

    def validate(self, password, user=None):
        if user is None:
            return
        email = (getattr(user, "email", "") or "").lower()
        full_name = (getattr(user, "full_name", "") or "").lower()
        pieces = [email, email.split("@")[0], *re.split(r"[\s.\-_]+", full_name)]
        lowered = password.lower()
        if any(len(piece) >= self.min_length and piece in lowered for piece in pieces):
            raise ValidationError(
                _("The password cannot contain your name or e-mail address."),
                code="password_contains_personal_info",
            )

    def get_help_text(self):
        return _("Does not contain your name or e-mail address.")
