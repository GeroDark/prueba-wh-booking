from .views import DatabaseHealthView, HealthView

HEALTH_PATHS = {
    "/health/": HealthView.as_view(),
    "/health/db/": DatabaseHealthView.as_view(),
}


class HealthCheckMiddleware:
    """Answer the health checks before any other middleware.

    The hosting provider's probe can arrive with an internal Host header (e.g. `localhost:10000`
    on Render) and over plain HTTP. Answering first means neither ALLOWED_HOSTS nor the HTTPS
    redirect can make a healthy service look broken.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        view = HEALTH_PATHS.get(request.path)
        if view is not None:
            return view(request)
        return self.get_response(request)
