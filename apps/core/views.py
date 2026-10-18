import logging

from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView

logger = logging.getLogger(__name__)


class HomeView(TemplateView):
    template_name = "pages/home.html"


class HealthView(View):
    """Liveness/readiness probe for the hosting provider: checks that the database answers."""

    def get(self, request, *args, **kwargs):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except DatabaseError:
            logger.exception("Health check failed: database unavailable")
            return JsonResponse({"status": "error", "database": "unavailable"}, status=503)
        return JsonResponse({"status": "ok"})
