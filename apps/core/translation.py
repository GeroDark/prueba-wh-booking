from modeltranslation.translator import TranslationOptions, register

from .models import (
    Banner,
    ContactChannel,
    FeatureItem,
    FeatureSection,
    HomePage,
    MenuGroup,
    MenuLink,
    SiteSettings,
)


@register(SiteSettings)
class SiteSettingsTranslation(TranslationOptions):
    fields = ("whatsapp_message",)


@register(HomePage)
class HomePageTranslation(TranslationOptions):
    fields = (
        "hero_title",
        "hero_subtitle",
        "destinations_title",
        "featured_title",
        "featured_text",
    )


@register(Banner)
class BannerTranslation(TranslationOptions):
    fields = ("title", "text", "cta_label", "cta_message")
    required_languages = ("es",)


@register(FeatureSection)
class FeatureSectionTranslation(TranslationOptions):
    fields = ("title", "text")
    required_languages = ("es",)


@register(FeatureItem)
class FeatureItemTranslation(TranslationOptions):
    fields = ("title", "description")
    required_languages = ("es",)


@register(MenuGroup)
class MenuGroupTranslation(TranslationOptions):
    fields = ("title",)


@register(MenuLink)
class MenuLinkTranslation(TranslationOptions):
    fields = ("label",)
    required_languages = ("es",)


@register(ContactChannel)
class ContactChannelTranslation(TranslationOptions):
    fields = ("label",)
