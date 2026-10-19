from django import forms
from django.conf import settings
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.forms import FriendlyErrorsMixin

from .models import User
from .phones import InvalidPhone, parse_phone, region_choices, region_for_prefix
from .validators import MAX_AGE, normalize_name, years_ago

# Browser-side hints only (the server validates again). The browser's own e-mail check accepts
# "name@gmail" without a dot in the domain; Django's validator does not, so the hint asks for it.
EMAIL_PATTERN = r"[^@\s]+@[^@\s]+\.[^@\s]+"
FULL_NAME_PATTERN = r"\s*[\p{L}\p{M}'’.\-]+(?:\s+[\p{L}\p{M}'’.\-]+)+\s*"


def email_widget(**attrs):
    return forms.EmailInput(attrs={"autocomplete": "email", "pattern": EMAIL_PATTERN, **attrs})


class SignUpForm(FriendlyErrorsMixin, forms.ModelForm):
    """Account creation with e-mail, full name and one password (shown/hidden by the user).

    The design has a single password field with a live checklist instead of a confirmation
    field; the "show password" button prevents typos. The checkout (phase 7) extends this form
    with the guest's personal details.
    """

    password = forms.CharField(
        label=_("Create a password"),
        strip=False,
        error_messages={"required": _("Create a password.")},
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "placeholder": _("Enter a new password"),
                "aria-describedby": "password-rules",
            }
        ),
    )

    class Meta:
        model = User
        fields = ("email", "full_name")
        error_messages = {
            "email": {"required": _("Enter your email address.")},
            "full_name": {"required": _("Enter your first and last name.")},
        }
        widgets = {
            "email": email_widget(placeholder=_("name@example.com")),
            "full_name": forms.TextInput(
                attrs={
                    "autocomplete": "name",
                    "placeholder": _("Enter your full name"),
                    "pattern": FULL_NAME_PATTERN,
                    "data-error-invalid": _("Enter your first and last name using letters only."),
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["full_name"].required = True

    def clean_email(self):
        email = User.objects.normalize_email(self.cleaned_data["email"])
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                _("An account with this email already exists. Sign in instead."),
                code="duplicate_email",
            )
        return email

    def clean_full_name(self):
        return normalize_name(self.cleaned_data["full_name"])

    def _post_clean(self):
        super()._post_clean()
        # The password is checked against what was typed in this same form, even when the
        # e-mail or the name have errors: otherwise "prueba123" with "prueba@gmail" would only
        # be rejected on the second attempt.
        password = self.cleaned_data.get("password")
        if password:
            typed = User(
                email=self.data.get(self.add_prefix("email"), "").strip(),
                full_name=self.data.get(self.add_prefix("full_name"), ""),
            )
            try:
                password_validation.validate_password(password, typed)
            except forms.ValidationError as error:
                self.add_error("password", error)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


# Personal details of the checkout (Figma "Información personal").
GUEST_DETAIL_FIELDS = ("full_name", "nationality", "phone_number", "birth_date")
GUEST_DETAIL_WIDGETS = {
    "phone_number": forms.TextInput(
        attrs={
            "autocomplete": "tel-national",
            "inputmode": "tel",
            "placeholder": _("Enter your phone number"),
            # ( ) escaped: browsers compile `pattern` with the regex v flag, which requires it.
            "pattern": r"[0-9 \(\)+.\-]{4,20}",
            "data-error-invalid": _("Use only digits, spaces or dashes."),
        }
    ),
    "birth_date": forms.DateInput(
        attrs={"type": "date", "autocomplete": "bday"}, format="%Y-%m-%d"
    ),
}
GUEST_DETAIL_ERRORS = {
    "full_name": {"required": _("Enter your first and last name.")},
    "nationality": {"required": _("Select your nationality.")},
    "phone_number": {"required": _("Enter your phone number.")},
    "birth_date": {"required": _("Enter your birth date.")},
}
INVALID_CHOICE = _("Select one of the available options.")


class GuestDetailsMixin:
    """Nationality, phone and birth date, all required to book (D12, D36).

    Shared by the sign-up of a new guest at checkout and by the form a signed-in guest sees when
    their profile is incomplete. The phone is validated for the chosen country and stored as
    prefix (+51) + national number; the prefix follows the number if it was typed with its own +.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in GUEST_DETAIL_FIELDS:
            self.fields[name].required = True
            self.fields[name].help_text = ""  # the model's help texts are written for the admin

        nationality = self.fields["nationality"]
        choices = [
            choice for choice in nationality.choices if choice[0] or choice[1] != "---------"
        ]
        nationality.choices = [("", _("Select your country")), *choices]
        nationality.error_messages["invalid_choice"] = INVALID_CHOICE

        self.fields["phone_region"] = forms.ChoiceField(
            label=_("Code"),
            choices=[("", _("Code")), *region_choices()],
            error_messages={"required": _("Select the code."), "invalid_choice": INVALID_CHOICE},
        )
        # Explicit opt-in, unchecked by default (GDPR in Spain, Law 29733 in Peru; D36).
        self.fields["newsletter"] = forms.BooleanField(
            label=_(
                "I want to receive exclusive member offers, inspiring content and news from "
                "Wynwood House by email."
            ),
            required=False,
        )

        user = self.instance
        self.initial.setdefault(
            "phone_region", region_for_prefix(user.phone_prefix) or user.nationality.code or ""
        )
        if user.pk:
            self.initial.setdefault("newsletter", user.marketing_opt_in)

        today = timezone.localdate()
        # The browser's date picker opens on dates that can pass validation.
        self.fields["birth_date"].widget.attrs.update(
            {
                "min": years_ago(today, MAX_AGE).isoformat(),
                "max": years_ago(today, settings.BOOKING_MIN_GUEST_AGE).isoformat(),
                "data-error-min": _("Check the year of your birth date."),
                "data-error-max": _("You must be at least %(age)s years old to book.")
                % {"age": settings.BOOKING_MIN_GUEST_AGE},
            }
        )

    def clean(self):
        cleaned = super().clean()
        raw, region = cleaned.get("phone_number"), cleaned.get("phone_region")
        if raw and region:
            try:
                phone = parse_phone(raw, region)
            except InvalidPhone as error:
                self.add_error("phone_number", error.message)
            else:
                cleaned["phone_number"] = phone.number
                self.instance.phone_prefix = phone.prefix
        if "newsletter" in cleaned:
            self.instance.set_marketing_consent(cleaned["newsletter"])
        return cleaned


class GuestDetailsForm(FriendlyErrorsMixin, GuestDetailsMixin, forms.ModelForm):
    """For a signed-in guest whose profile lacks some of the details."""

    class Meta:
        model = User
        fields = GUEST_DETAIL_FIELDS
        widgets = {**SignUpForm.Meta.widgets, **GUEST_DETAIL_WIDGETS}
        error_messages = GUEST_DETAIL_ERRORS

    def clean_full_name(self):
        return normalize_name(self.cleaned_data["full_name"])


class CheckoutSignUpForm(GuestDetailsMixin, SignUpForm):
    """Sign-up inside the checkout (Figma "Página registro"): the account plus the details."""

    class Meta(SignUpForm.Meta):
        fields = ("email", *GUEST_DETAIL_FIELDS)
        widgets = {**SignUpForm.Meta.widgets, **GUEST_DETAIL_WIDGETS}
        error_messages = {**SignUpForm.Meta.error_messages, **GUEST_DETAIL_ERRORS}


class EmailAuthenticationForm(FriendlyErrorsMixin, AuthenticationForm):
    """Login with e-mail. The error never says which of the two fields was wrong
    (it would let anyone find out which e-mails have an account)."""

    username = forms.EmailField(
        label=_("Email"),
        error_messages={"required": _("Enter your email address.")},
        widget=email_widget(autofocus=True),
    )
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        error_messages={"required": _("Enter your password.")},
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": _("The email or password is incorrect."),
    }
