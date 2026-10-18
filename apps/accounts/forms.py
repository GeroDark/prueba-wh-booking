from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _

from apps.core.forms import FriendlyErrorsMixin

from .models import User
from .validators import normalize_name

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
            "email": email_widget(placeholder="nombre@ejemplo.com"),
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
