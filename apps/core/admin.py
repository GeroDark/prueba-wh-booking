from django.contrib import admin
from django.db import models
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from modeltranslation.admin import (
    TranslationAdmin,
    TranslationStackedInline,
    TranslationTabularInline,
)

from .models import (
    Banner,
    ContactChannel,
    FeatureItem,
    FeatureSection,
    HomePage,
    MenuGroup,
    MenuLink,
    SiteSettings,
    SocialLink,
)

admin.site.site_header = _("Wynwood House administration")
admin.site.site_title = "Wynwood House"
admin.site.index_title = _("Content and bookings")


def image_thumbnail(field_file, height=60):
    if not field_file:
        return "-"
    return format_html(
        '<img src="{}" alt="" style="height:{}px;border-radius:4px">', field_file.url, height
    )


class SingletonAdmin(admin.ModelAdmin):
    """Edit the single row directly: the list view jumps to it and it cannot be deleted."""

    def has_add_permission(self, request):
        return not self.model.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = self.model.load()
        opts = self.model._meta
        return redirect(reverse(f"admin:{opts.app_label}_{opts.model_name}_change", args=[obj.pk]))


# URLs typed without a scheme are assumed to be https (Django's default changes to that in 6.0).
HTTPS_URL_FIELDS = {models.URLField: {"assume_scheme": "https"}}


@admin.register(SiteSettings)
class SiteSettingsAdmin(SingletonAdmin, TranslationAdmin):
    formfield_overrides = HTTPS_URL_FIELDS
    fieldsets = (
        (_("Contact"), {"fields": ("contact_email", "whatsapp_number", "whatsapp_message")}),
        (_("Mobile app"), {"fields": ("app_store_url", "play_store_url")}),
    )


@admin.register(HomePage)
class HomePageAdmin(SingletonAdmin, TranslationAdmin):
    readonly_fields = ("hero_preview",)
    fieldsets = (
        (_("Hero"), {"fields": ("hero_title", "hero_subtitle", "hero_image", "hero_preview")}),
        (_("Destinations"), {"fields": ("destinations_title",)}),
        (_("Featured properties"), {"fields": ("featured_title", "featured_text")}),
    )

    @admin.display(description=_("preview"))
    def hero_preview(self, obj):
        return image_thumbnail(obj.hero_image, height=120)


@admin.register(Banner)
class BannerAdmin(TranslationAdmin):
    list_display = ("title", "key", "layout", "thumbnail", "order", "is_active")
    list_editable = ("order", "is_active")
    readonly_fields = ("thumbnail",)
    fieldsets = (
        (None, {"fields": ("key", "title", "text", "image", "thumbnail", "layout")}),
        (_("Button"), {"fields": ("cta_label", "cta_target", "cta_url")}),
        (_("Visibility"), {"fields": ("order", "is_active")}),
    )

    @admin.display(description=_("image"))
    def thumbnail(self, obj):
        return image_thumbnail(obj.image)


class FeatureItemInline(TranslationStackedInline):
    model = FeatureItem
    extra = 0
    fields = ("title", "description", "image", "thumbnail", "order")
    readonly_fields = ("thumbnail",)

    @admin.display(description=_("preview"))
    def thumbnail(self, obj):
        return image_thumbnail(obj.image)


@admin.register(FeatureSection)
class FeatureSectionAdmin(TranslationAdmin):
    list_display = ("title", "key", "item_count", "is_active")
    inlines = [FeatureItemInline]

    @admin.display(description=_("items"))
    def item_count(self, obj):
        return obj.items.count()


class MenuLinkInline(TranslationTabularInline):
    model = MenuLink
    extra = 0


@admin.register(MenuGroup)
class MenuGroupAdmin(TranslationAdmin):
    list_display = ("__str__", "placement", "order", "is_active")
    list_filter = ("placement",)
    list_editable = ("order", "is_active")
    inlines = [MenuLinkInline]


@admin.register(ContactChannel)
class ContactChannelAdmin(TranslationAdmin):
    list_display = ("value", "kind", "label", "country_code", "order", "is_active")
    list_filter = ("kind",)
    list_editable = ("order", "is_active")


@admin.register(SocialLink)
class SocialLinkAdmin(admin.ModelAdmin):
    formfield_overrides = HTTPS_URL_FIELDS
    list_display = ("network", "url", "order", "is_active")
    list_editable = ("order", "is_active")
