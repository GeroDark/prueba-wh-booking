"""Which holds belong to this visitor.

An anonymous visitor has no user yet (they register during checkout), so ownership of a hold is
proven by its reference stored in their session. Django keeps the session data when the visitor
logs in, so the hold survives the login step.
"""

SESSION_KEY = "booking_holds"


def session_holds(request):
    return list(request.session.get(SESSION_KEY, []))


def remember_hold(request, reference):
    # Only the latest hold is kept: one active hold per visitor (D08).
    request.session[SESSION_KEY] = [reference]


def forget_hold(request, reference):
    request.session[SESSION_KEY] = [ref for ref in session_holds(request) if ref != reference]


def owns_booking(request, booking):
    if booking.guest_id is not None:
        return request.user.is_authenticated and booking.guest_id == request.user.pk
    return booking.reference in session_holds(request)
