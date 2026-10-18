from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _

from .models import User


class SignUpForm(forms.ModelForm):
    """Account creation with e-mail, full name and one password (shown/hidden by the user).

    The design has a single password field with a live checklist instead of a confirmation
    field; the "show password" button prevents typos. The checkout (phase 7) extends this form
    with the guest's personal details.
    """

    password = forms.CharField(
        label=_("Create a password"),
        strip=False,
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
        widgets = {
            "email": forms.EmailInput(
                attrs={"autocomplete": "email", "placeholder": "nombre@ejemplo.com"}
            ),
            "full_name": forms.TextInput(
                attrs={"autocomplete": "name", "placeholder": _("Enter your full name")}
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

    def _post_clean(self):
        super()._post_clean()
        # Validate the password against the data typed in this same form (name, e-mail),
        # once the instance has them.
        password = self.cleaned_data.get("password")
        if password:
            try:
                password_validation.validate_password(password, self.instance)
            except forms.ValidationError as error:
                self.add_error("password", error)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class EmailAuthenticationForm(AuthenticationForm):
    """Login with e-mail. The error never says which of the two fields was wrong
    (it would let anyone find out which e-mails have an account)."""

    username = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True}),
    )
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": _("The email or password is incorrect."),
    }
