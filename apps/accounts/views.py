from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect, resolve_url
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import get_language
from django.utils.translation import gettext as _
from django.views.generic import CreateView

from .forms import EmailAuthenticationForm, SignUpForm


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
