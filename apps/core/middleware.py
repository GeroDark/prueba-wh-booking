from .views import HealthView

HEALTH_PATH = "/health/"


class HealthCheckMiddleware:
    """Answer the hosting provider's health probe before any other middleware.

    The probe can arrive with an internal Host header (e.g. `localhost:10000` on Render) and over
    plain HTTP. Answering first means neither ALLOWED_HOSTS nor the HTTPS redirect can make a
    healthy service look broken. It still checks the database (HealthView).
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.health = HealthView.as_view()

    def __call__(self, request):
        if request.path == HEALTH_PATH:
            return self.health(request)
        return self.get_response(request)
