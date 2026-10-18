import pytest
from django.contrib import admin
from django.urls import reverse

from apps.core.models import HomePage, SiteSettings

pytestmark = pytest.mark.django_db

REGISTERED = [
    (model._meta.app_label, model._meta.model_name)
    for model in admin.site._registry
    if model._meta.app_label in {"core", "properties", "accounts"}
]
SINGLETONS = {"homepage", "sitesettings"}


@pytest.mark.parametrize(("app_label", "model_name"), REGISTERED)
def test_admin_list_and_add_pages_render(admin_client, app_label, model_name):
    changelist = admin_client.get(reverse(f"admin:{app_label}_{model_name}_changelist"))
    assert changelist.status_code in (200, 302)

    if model_name not in SINGLETONS:
        add = admin_client.get(reverse(f"admin:{app_label}_{model_name}_add"))
        assert add.status_code in (200, 403)  # 403: models editable only inline (districts)


@pytest.mark.parametrize("model", [HomePage, SiteSettings])
def test_singleton_list_page_opens_its_only_row(admin_client, model):
    opts = model._meta

    response = admin_client.get(reverse(f"admin:{opts.app_label}_{opts.model_name}_changelist"))

    assert response.status_code == 302
    assert response["Location"] == reverse(
        f"admin:{opts.app_label}_{opts.model_name}_change", args=[model.SINGLETON_PK]
    )


def test_property_form_shows_both_languages(admin_client):
    html = admin_client.get(reverse("admin:properties_property_add")).text

    assert 'name="title_es"' in html
    assert 'name="title_en"' in html
