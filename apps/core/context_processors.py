from django.db.models import Prefetch
from django.utils.functional import SimpleLazyObject

from apps.properties.forms import SearchForm
from apps.properties.models import Country

from .models import ContactChannel, MenuGroup, MenuLink, SiteSettings, SocialLink


def _menus(placement):
    return list(
        MenuGroup.objects.filter(placement=placement, is_active=True).prefetch_related(
            Prefetch("links", queryset=MenuLink.objects.order_by("order", "id"))
        )
    )


def _contact_channels():
    """Split active channels into the footer's two columns: WhatsApp and everything else."""
    channels = list(ContactChannel.objects.filter(is_active=True).order_by("order", "id"))
    whatsapp = [c for c in channels if c.kind == ContactChannel.Kind.WHATSAPP]
    others = [c for c in channels if c.kind != ContactChannel.Kind.WHATSAPP]
    return {"whatsapp": whatsapp, "others": others}


def site(request):
    """Data for the header and footer, shared by every page.

    Values are lazy: a page only queries what its templates actually render
    (the admin, for instance, renders neither the header nor the footer).
    """
    return {
        "site_settings": SimpleLazyObject(SiteSettings.load),
        "header_menu": SimpleLazyObject(lambda: _menus(MenuGroup.Placement.HEADER)),
        "footer_menus": SimpleLazyObject(lambda: _menus(MenuGroup.Placement.FOOTER)),
        "contact_channels": SimpleLazyObject(_contact_channels),
        "social_links": SimpleLazyObject(lambda: list(SocialLink.objects.filter(is_active=True))),
        "footer_destinations": SimpleLazyObject(
            lambda: list(Country.objects.filter(is_active=True))
        ),
        "footer_search_form": SimpleLazyObject(lambda: SearchForm(auto_id="footer_%s")),
    }
