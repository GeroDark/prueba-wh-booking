from axes.utils import reset as axes_reset
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect, resolve_url
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import get_language
from django.utils.translation import gettext as _
from django.views.generic import CreateView

from .emails import email_frame_context, send_password_changed_notice
from .forms import EmailAuthenticationForm, NewPasswordForm, PasswordResetRequestForm, SignUpForm
from .lockout import lockout_username


class SafeNextMixin:
    """`?next=` is only followed when it points to this site (prevents open redirects)."""

    def get_next_url(self):
        candidate = self.request.POST.get("next") or self.request.GET.get("next")
        if candidate and url_has_allowed_host_and_scheme(
            candidate,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        ):
            return candidate
        return resolve_url(settings.LOGIN_REDIRECT_URL)


class SignUpView(SafeNextMixin, CreateView):
    form_class = SignUpForm
    template_name = "pages/accounts/signup.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(self.get_next_url())
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.preferred_language = get_language()
        user = form.save()
        # Signed in right away: logging in keeps the session data, so a hold made before
        # signing up still belongs to this visitor.
        login(self.request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(
            self.request, _("Welcome to Wynwood House, %(name)s!") % {"name": user.get_short_name()}
        )
        return redirect(self.get_next_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["next"] = self.get_next_url()
        return context


class LoginView(auth_views.LoginView):
    form_class = EmailAuthenticationForm
    template_name = "pages/accounts/login.html"
    redirect_authenticated_user = True


class LogoutView(auth_views.LogoutView):
    """POST only (Django 5): a link or an image tag cannot log anyone out."""


class PasswordResetView(auth_views.PasswordResetView):
    """Ask for a reset link (D43). The e-mail goes out in the language of the page, and its link
    is built from SITE_URL, not from the request's Host header, which an attacker could set to
    their own domain ("password reset poisoning")."""

    form_class = PasswordResetRequestForm
    template_name = "pages/accounts/password_reset.html"
    subject_template_name = "emails/password_reset_subject.txt"
    email_template_name = "emails/password_reset.txt"
    html_email_template_name = "emails/password_reset.html"
    success_url = reverse_lazy("accounts:password_reset_done")

    def form_valid(self, form):
        self.extra_email_context = {
            **email_frame_context(),
            "valid_minutes": settings.PASSWORD_RESET_TIMEOUT // 60,
        }
        return super().form_valid(form)


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = "pages/accounts/password_reset_done.html"


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    """New password from the link. The link works once: the token depends on the password, so
    changing it invalidates the link, and the guest's other sessions are closed too."""

    form_class = NewPasswordForm
    template_name = "pages/accounts/password_reset_confirm.html"
    post_reset_login = True
    post_reset_login_backend = "django.contrib.auth.backends.ModelBackend"
    success_url = reverse_lazy("core:home")

    def form_valid(self, form):
        response = super().form_valid(form)
        # Whoever opened the link controls the e-mail: the failed sign-in limit (D41) no longer
        # applies to them, on any network. Signing in only clears this network's failures.
        axes_reset(username=lockout_username(self.request, {"username": form.user.email}))
        send_password_changed_notice(form.user)
        messages.success(self.request, _("Your password has been updated. You are signed in."))
        return response
