"""The visitor's IP address, for abuse limits (D41).

Behind a proxy, REMOTE_ADDR is the proxy, not the visitor. The real address comes in a header,
and only a header that the proxy *overwrites* can be trusted: anyone can send their own
X-Forwarded-For, and some proxies only append to it.

Render sits behind Cloudflare, which sets CF-Connecting-IP to the address that connected to it and
replaces any value sent by the client. CLIENT_IP_HEADER names that header in production; without a
proxy (local development, tests) REMOTE_ADDR is the visitor.
"""

import hashlib
import hmac
import ipaddress

from django.conf import settings


def client_ip(request):
    header = settings.CLIENT_IP_HEADER
    value = request.META.get(header, "").strip() if header else ""
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        return request.META.get("REMOTE_ADDR", "")


def hashed_client_ip(request):
    """A keyed hash of the IP: enough to count holds per visitor without storing the address."""
    ip = client_ip(request)
    if not ip:
        return ""
    return hmac.new(settings.SECRET_KEY.encode(), ip.encode(), hashlib.sha256).hexdigest()[:32]
