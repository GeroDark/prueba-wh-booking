"""The booking flow in a real browser, as a guest would go through it."""

import re
from datetime import timedelta

import pytest
from django.utils import timezone
from playwright.sync_api import expect

from apps.bookings.models import Booking
from apps.bookings.tests.factories import BookingFactory
from apps.payments.models import Payment
from apps.properties.tests.factories import (
    CityFactory,
    CountryFactory,
    DistrictFactory,
    PropertyFactory,
)

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

    # And it is listed in "My bookings", in the header's account menu (D44).
    page.click(".account-menu__toggle")
    page.click(".account-menu >> text=Mis reservas")
    expect(page.locator("#upcoming-title")).to_have_text("Próximas estadías")
    expect(page.locator(".booking-item")).to_contain_text(booking.reference)


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


# The search calendar's first arrival, read from the flatpickr instance (open or not).
DAY_IS_DISABLED = """([selector, iso]) => {
  const picker = document.querySelector(selector)._flatpickr;
  picker.jumpToDate(iso);
  const p = n => String(n).padStart(2, '0');
  const isoOf = date => `${date.getFullYear()}-${p(date.getMonth() + 1)}-${p(date.getDate())}`;
  const cell = [...picker.daysContainer.querySelectorAll('.flatpickr-day')]
    .filter(d => !d.classList.contains('prevMonthDay') && !d.classList.contains('nextMonthDay'))
    .find(d => isoOf(d.dateObj) === iso);
  return cell.classList.contains('flatpickr-disabled');
}"""


@pytest.fixture
def far_apart_cities(transactional_db):
    """Baker Island (UTC-12) and Kiritimati (UTC+14) are 26 hours apart: never on the same date."""

    def make(slug, tz, code):
        country = CountryFactory(code=code, name_es=slug, name_en=slug, slug=slug)
        city = CityFactory(country=country, slug=slug, name_es=slug, name_en=slug, timezone=tz)
        PropertyFactory(district=DistrictFactory(city=city))
        return city

    return make("baker", "Etc/GMT+12", "um"), make("kiritimati", "Pacific/Kiritimati", "ki")


def test_the_search_calendar_follows_the_destinations_date(
    new_context, live_server, far_apart_cities
):
    """Second review: the search calendar took "today" from the device. A guest whose device
    is already on the next day must still be offered today's arrival where the destination is."""
    baker, kiritimati = far_apart_cities
    baker_today = baker.local_today()
    assert kiritimati.local_today() > baker_today

    page = new_context(timezone_id="Pacific/Kiritimati").new_page()  # device ahead
    page.goto(f"{live_server.url}/es/")
    page.select_option("#id_city", "baker")
    page.locator("#id_check_in").click()

    assert not page.evaluate(DAY_IS_DISABLED, ["#id_check_in", baker_today.isoformat()])
    click_day(page, baker_today)
    assert page.locator("input[name=check_in]").first.input_value() == baker_today.isoformat()

    # There it is already the next day: that arrival is past and is cleared.
    page.select_option("#id_city", "kiritimati")
    assert page.evaluate(DAY_IS_DISABLED, ["#id_check_in", baker_today.isoformat()])
    assert page.locator("input[name=check_in]").first.input_value() == ""
