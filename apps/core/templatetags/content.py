from django import template
from django.utils.html import format_html

register = template.Library()


@register.simple_tag(takes_context=True)
def banner_cta_url(context, banner):
    """Button URL of a banner; WhatsApp buttons use the number from the site settings."""
    return banner.get_cta_url(context["site_settings"])


@register.simple_tag(takes_context=True)
def contact_href(context, channel):
    """Link of a contact channel; WhatsApp chats open with the site's general message."""
    return channel.get_href(whatsapp_message=context["site_settings"].whatsapp_message)


@register.simple_tag(takes_context=True)
def whatsapp_link(context, message=""):
    """Chat link to the site's WhatsApp number with a specific pre-filled message."""
    return context["site_settings"].get_whatsapp_url(message)


@register.filter
def email_break(address):
    """Let long e-mail addresses wrap after the @ instead of overflowing narrow columns."""
    local, at, domain = str(address).partition("@")
    if not at:
        return address
    return format_html("{}@<wbr>{}", local, domain)
