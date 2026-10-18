from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def banner_cta_url(context, banner):
    """Button URL of a banner; WhatsApp buttons use the number from the site settings."""
    return banner.get_cta_url(context["site_settings"])
