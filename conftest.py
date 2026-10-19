import pytest
from django.conf import settings as django_settings
from django.utils import translation


@pytest.fixture(autouse=True)
def _default_language():
    """Every test starts in the default language. A request to /en/ leaves English active in
    the thread, and a later test that renders without a request would inherit it."""
    translation.activate(django_settings.LANGUAGE_CODE)
    yield
    translation.deactivate()


@pytest.fixture(autouse=True)
def _test_settings(settings, tmp_path):
    """Plain HTTP test client, no collected static files, uploads in a throwaway folder."""
    settings.SECURE_SSL_REDIRECT = False
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    settings.MEDIA_ROOT = tmp_path / "media"
    # Hashing passwords with the production algorithm makes tests slow for no benefit.
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
