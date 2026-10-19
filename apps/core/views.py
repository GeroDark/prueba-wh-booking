import logging

from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView

from apps.properties.forms import SearchForm
from apps.properties.models import Country, Property

from .models import Banner, FeatureSection, HomePage

logger = logging.getLogger(__name__)

FEATURED_LIMIT = 8


class HomeView(TemplateView):
    template_name = "pages/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sections = FeatureSection.objects.filter(is_active=True).prefetch_related("items")
        context.update(
            home=HomePage.load(),
            search_form=SearchForm(),
            destinations=Country.objects.filter(is_active=True).exclude(image=""),
            featured_properties=(
                Property.objects.active().featured().with_card_data()[:FEATURED_LIMIT]
            ),
            # Keys become template-friendly: "why-spain" -> sections.why_spain
            sections={section.key.replace("-", "_"): section for section in sections},
            banners=Banner.objects.filter(is_active=True),
        )
        return context


class HealthView(View):
    """`/health/`: the app is up (liveness). No database query on purpose (D39).

    The host calls it every few seconds and the uptime monitor every few minutes. Querying the
    database here would keep the free Neon database awake all the time and use up its monthly
    compute, which would take the whole site down.
    """

    def get(self, request, *args, **kwargs):
        return JsonResponse({"status": "ok"})


class DatabaseHealthView(View):
    """`/health/db/`: the database answers too. For manual checks, not for frequent probes."""

    def get(self, request, *args, **kwargs):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except DatabaseError:
            logger.exception("Health check failed: database unavailable")
            return JsonResponse({"status": "error", "database": "unavailable"}, status=503)
        return JsonResponse({"status": "ok"})
