from django.urls import path

from .views import (
    BookingConfirmationView,
    CheckoutView,
    MyBookingsView,
    QuoteView,
    ReleaseHoldView,
)

app_name = "bookings"

urlpatterns = [
    path("properties/<slug:slug>/quote/", QuoteView.as_view(), name="quote"),
    path("checkout/<str:reference>/", CheckoutView.as_view(), name="checkout"),
    path("checkout/<str:reference>/release/", ReleaseHoldView.as_view(), name="release"),
    path("bookings/", MyBookingsView.as_view(), name="list"),
    path("bookings/<str:reference>/", BookingConfirmationView.as_view(), name="confirmation"),
]
