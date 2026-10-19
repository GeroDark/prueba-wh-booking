"""Production pieces: Cloudinary storage, admin bootstrap, seeding once and the health probe."""

import io

import cloudinary
import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client

from apps.core.storage import CloudinaryMediaStorage
from apps.properties.models import Property
from apps.properties.tests.factories import PropertyFactory

User = get_user_model()


# Cloudinary storage (the SDK calls are replaced: no network in tests)


@pytest.fixture
def cloud(monkeypatch):
    calls = {"uploads": [], "destroyed": [], "stored": set()}

    def upload(content, public_id, **options):
        calls["uploads"].append((public_id, content.read(), options))
        calls["stored"].add(public_id)

    def resource(public_id, **options):
        if public_id not in calls["stored"]:
            raise cloudinary.exceptions.NotFound("missing")
        return {"bytes": 1234}

    monkeypatch.setattr("cloudinary.uploader.upload", upload)
    monkeypatch.setattr(
        "cloudinary.uploader.destroy", lambda pid, **o: calls["destroyed"].append(pid)
    )
    monkeypatch.setattr("cloudinary.api.resource", resource)
    cloudinary.config(cloud_name="demo-cloud", api_key="key", api_secret="secret")
    return calls


def test_storage_uploads_the_optimized_file_as_it_is(cloud):
    storage = CloudinaryMediaStorage(folder="wh-booking")

    name = storage.save("properties/loft.webp", ContentFile(b"webp-bytes"))

    public_id, content, options = cloud["uploads"][0]
    assert name == "properties/loft.webp"
    assert public_id == "wh-booking/properties/loft"
    assert content == b"webp-bytes"
    assert options["resource_type"] == "image"


def test_storage_urls_point_to_the_cdn_with_https(cloud):
    url = CloudinaryMediaStorage(folder="wh-booking").url("properties/loft.webp")

    assert url.startswith("https://res.cloudinary.com/demo-cloud/image/upload/")
    assert url.endswith("wh-booking/properties/loft.webp")


def test_storage_exists_size_and_delete(cloud):
    storage = CloudinaryMediaStorage(folder="wh-booking")
    assert not storage.exists("email/copy.jpg")

    storage.save("email/copy.jpg", ContentFile(b"jpg"))

    assert storage.exists("email/copy.jpg")
    assert storage.size("email/copy.jpg") == 1234
    storage.delete("email/copy.jpg")
    assert cloud["destroyed"] == ["wh-booking/email/copy"]


def test_storage_reads_files_back_from_the_cdn(cloud, monkeypatch):
    monkeypatch.setattr("apps.core.storage.urlopen", lambda url, timeout: io.BytesIO(b"image"))

    with CloudinaryMediaStorage(folder="wh-booking").open("properties/loft.webp") as handle:
        assert handle.read() == b"image"


# Admin account from environment variables


@pytest.mark.django_db
def test_ensure_superuser_creates_the_admin_once(monkeypatch):
    monkeypatch.setenv("DJANGO_SUPERUSER_EMAIL", "admin@wynwoodhouse.test")
    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "Luna-Mar-Cielo-7")

    call_command("ensure_superuser")
    call_command("ensure_superuser")  # every restart: nothing changes

    admin = User.objects.get()
    assert admin.is_superuser and admin.is_staff
    assert admin.check_password("Luna-Mar-Cielo-7")


@pytest.mark.django_db
def test_ensure_superuser_does_nothing_without_the_variables(monkeypatch):
    monkeypatch.delenv("DJANGO_SUPERUSER_EMAIL", raising=False)
    monkeypatch.delenv("DJANGO_SUPERUSER_PASSWORD", raising=False)

    call_command("ensure_superuser")

    assert not User.objects.exists()


@pytest.mark.django_db
def test_ensure_superuser_refuses_a_weak_password(monkeypatch):
    monkeypatch.setenv("DJANGO_SUPERUSER_EMAIL", "admin@wynwoodhouse.test")
    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "password123")

    with pytest.raises(CommandError, match="DJANGO_SUPERUSER_PASSWORD"):
        call_command("ensure_superuser")

    assert not User.objects.exists()


# Demo data only on the first start


@pytest.mark.django_db
def test_seed_if_empty_keeps_existing_content():
    PropertyFactory()

    call_command("seed_data", "--if-empty", "--skip-images")

    assert Property.objects.count() == 1  # admin edits survive restarts


# Health probe


@pytest.mark.django_db
def test_health_probe_answers_with_an_internal_host_over_http(settings):
    settings.ALLOWED_HOSTS = ["wh-booking.onrender.com"]
    settings.SECURE_SSL_REDIRECT = True

    response = Client(HTTP_HOST="localhost:10000").get("/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_other_paths_still_validate_the_host(settings):
    settings.ALLOWED_HOSTS = ["wh-booking.onrender.com"]

    response = Client(HTTP_HOST="evil.example").get("/es/")

    assert response.status_code == 400
