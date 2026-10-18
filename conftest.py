import pytest


@pytest.fixture(autouse=True)
def _test_settings(settings):
    """Test client talks plain HTTP and static files are not collected during tests."""
    settings.SECURE_SSL_REDIRECT = False
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
