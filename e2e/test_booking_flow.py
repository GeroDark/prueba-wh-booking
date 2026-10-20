"""The booking flow in a real browser, as a guest would go through it."""

import re
from datetime import timedelta

import pytest
from django.utils import timezone
from playwright.sync_api import expect

from apps.bookings.models import Booking
from apps.bookings.tests.factories import BookingFactory
from apps.payments.models import Payment

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]

APPROVED, DECLINED = "4242 4242 4242 4242", "4000 0000 0000 0002"


def day(n):
    return timezone.localdate() + timedelta(days=n)


# Each calendar day gets its ISO date, so a test can click "2026-10-21" reliably.
TAG_DAYS = """() => {
  const days = document.querySelectorAll('.flatpickr-calendar.open .flatpickr-day');
  const p = n => String(n).padStart(2, '0');
  days.forEach(d => {
    if (!d.dateObj) return;
    const date = d.dateObj;
    d.dataset.iso = `${date.getFullYear()}-${p(date.getMonth() + 1)}-${p(date.getDate())}`;
  });
}"""


def click_day(page, target):
    """Click a day of the open calendar, moving to the next month if needed."""
    for _ in range(13):
        page.evaluate(TAG_DAYS)
        cell = page.locator(
            f".flatpickr-calendar.open .flatpickr-day[data-iso='{target.isoformat()}']"
            ":not(.prevMonthDay):not(.nextMonthDay)"
        )
        if cell.count():
            cell.first.click()
            return
        page.locator(".flatpickr-calendar.open .flatpickr-next-month").click()
    raise AssertionError(f"{target} not found in the calendar")


def pick_dates(page, arrival, departure):
    page.locator("#booking [data-date-range] input[type=text]").click()
    click_day(page, arrival)
    click_day(page, departure)


def sign_up_in_checkout(page, email):
    page.fill("#id_email", email)
    page.fill("#id_password", "Luna-Mar-Cielo-7")
    page.fill("#id_full_name", "Ana Torres")
    page.select_option("#id_nationality", "PE")  # the phone code follows it
    page.fill("#id_phone_number", "987 654 321")
    page.fill("#id_birth_date", "1990-05-14")
    page.click(".checkout__submit")


def pay_with(page, card):
    page.click(f"[data-test-card='{card}']")
    page.click(".checkout__submit")


def test_search_book_sign_up_decline_and_pay(page, live_server, prop, mailoutbox):
    """Search -> property -> calendar -> sign up -> declined card -> retry -> confirmation."""
    page.goto(f"{live_server.url}/es/")
    page.select_option("#id_city", "bogota")
    page.locator("form.search-bar button[type=submit]").first.click()
    expect(page.locator(".property-card")).to_have_count(1)

    page.locator(".property-card a").first.click()
    expect(page.locator("#property-title")).to_contain_text("Dúplex en Parque Virrey")
    pick_dates(page, day(5), day(8))
    expect(page.locator("#booking")).to_contain_text("3 noches")  # live quote from the server
    page.locator("#booking button[type=submit]").click()

    expect(page).to_have_url(re.compile(r"/es/checkout/WH-"))
    sign_up_in_checkout(page, "ana.torres@example.com")
    expect(page.locator("#payment-title")).to_be_visible()

    pay_with(page, DECLINED)
    expect(page.locator(".form-alert")).to_contain_text("rechazada")
    pay_with(page, APPROVED)

    expect(page).to_have_url(re.compile(r"/es/bookings/WH-"))
    expect(page.locator("body")).to_contain_text("Calle 88 # 15-23")  # exact address
    booking = Booking.objects.get()
    assert booking.status == Booking.Status.CONFIRMED
    assert list(booking.payments.values_list("status", flat=True).order_by("created_at")) == [
        Payment.Status.FAILED,
        Payment.Status.SUCCEEDED,
    ]
    assert len(mailoutbox) == 1
    assert mailoutbox[0].subject == f"Tu reserva {booking.reference} está confirmada"


def test_english_on_a_phone(page, live_server, prop, mailoutbox):
    page.set_viewport_size({"width": 375, "height": 812})
    page.goto(
        f"{live_server.url}/en/properties/{prop.slug}/"
        f"?check_in={day(10)}&check_out={day(12)}&guests=2"
    )
    page.locator("#booking button[type=submit]").click()

    sign_up_in_checkout(page, "sam.lee@example.com")
    pay_with(page, APPROVED)

    expect(page).to_have_url(re.compile(r"/en/bookings/WH-"))
    expect(page.locator("body")).to_contain_text("is confirmed")
    assert not page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
    assert mailoutbox[0].subject.startswith("Your booking WH-")


def test_an_expired_hold_sends_the_guest_back_with_the_same_dates(page, live_server, prop):
    page.goto(
        f"{live_server.url}/es/properties/{prop.slug}/"
        f"?check_in={day(5)}&check_out={day(7)}&guests=1"
    )
    page.locator("#booking button[type=submit]").click()
    expect(page).to_have_url(re.compile(r"/checkout/"))

    # The guest took longer than the hold.
    Booking.objects.update(expires_at=timezone.now() - timedelta(minutes=1))
    sign_up_in_checkout(page, "late.guest@example.com")

    expect(page).to_have_url(re.compile(rf"/es/properties/{prop.slug}/\?check_in={day(5)}"))
    expect(page.locator("body")).to_contain_text("se liberaron")
    page.locator("#booking button[type=submit]").click()  # same dates, one click
    expect(page).to_have_url(re.compile(r"/checkout/"))


def test_departure_on_the_day_another_booking_starts(page, live_server, prop):
    BookingFactory(property=prop, check_in=day(10), check_out=day(12))  # confirmed

    page.goto(f"{live_server.url}/es/properties/{prop.slug}/")
    pick_dates(page, day(8), day(10))  # leave the morning the other guest arrives

    expect(page.locator("#booking")).to_contain_text("2 noches")
    page.locator("#booking button[type=submit]").click()
    expect(page).to_have_url(re.compile(r"/checkout/"))
    assert Booking.objects.filter(status=Booking.Status.PENDING, check_out=day(10)).exists()
