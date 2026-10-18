import pytest


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
