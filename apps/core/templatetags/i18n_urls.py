from django import template
from django.urls import translate_url

register = template.Library()


@register.simple_tag(takes_context=True)
def translated_url(context, language_code):
    """URL of the current page in another language, e.g. /en/search/?q=1 -> /es/search/?q=1.

    It must be computed while rendering the page: the active language then matches the URL
    prefix, so Django can resolve it. Django's set_language view tries the same translation
    later, but with the language taken from the cookie or Accept-Language header, which fails
    when they differ from the page prefix and leaves the visitor on the original language.
    """
    return translate_url(context["request"].get_full_path(), language_code)
