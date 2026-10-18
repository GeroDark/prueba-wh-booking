"""Payment providers behind one interface (D11).

The checkout only talks to `PaymentGateway`. The simulated gateway is used in the demo; a real
provider (dLocal, Stripe) would be another subclass selected with the PAYMENT_GATEWAY setting.
"""

from dataclasses import dataclass

from django.conf import settings
from django.utils.module_loading import import_string


@dataclass(frozen=True)
class ChargeResult:
    succeeded: bool
    reference: str = ""  # the provider's id of the charge
    decline_code: str = ""


class PaymentGateway:
    def charge(self, *, amount, currency, card, idempotency_key, description):
        """Charge the card and return a ChargeResult.

        Must be idempotent: called again with the same key, it returns the first result and
        never charges twice (real providers offer this for retries after network errors).
        """
        raise NotImplementedError


class SimulatedGateway(PaymentGateway):
    """Approves or declines only the documented test cards. Any other card is declined, so a
    real card typed into the demo is never "charged", not even in appearance."""

    TEST_CARDS = {
        "4242424242424242": "",  # Visa: approved
        "5555555555554444": "",  # Mastercard: approved
        "378282246310005": "",  # American Express: approved
        "4000000000000002": "card_declined",
        "4000000000009995": "insufficient_funds",
    }

    @classmethod
    def test_cards(cls):
        """[("4242 4242 4242 4242", ""), ...] for the hint shown at checkout."""
        return [
            (" ".join(number[i : i + 4] for i in range(0, len(number), 4)), code)
            for number, code in cls.TEST_CARDS.items()
        ]

    def charge(self, *, amount, currency, card, idempotency_key, description):
        decline_code = self.TEST_CARDS.get(card.number, "test_card_required")
        if decline_code:
            return ChargeResult(succeeded=False, decline_code=decline_code)
        # Derived from the key: the same key always gives the same charge.
        return ChargeResult(succeeded=True, reference=f"sim_{idempotency_key.hex[:24]}")


def get_gateway():
    return import_string(settings.PAYMENT_GATEWAY)()
