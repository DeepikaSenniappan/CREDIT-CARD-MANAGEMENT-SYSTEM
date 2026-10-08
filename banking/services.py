from decimal import Decimal

from django.conf import settings


def simulate_payment(amount: Decimal) -> tuple[bool, str]:
    """Deterministic demo gateway; replace with a PCI-compliant provider integration."""
    failure_limit = Decimal(settings.PAYMENT_SIMULATOR_FAIL_ABOVE_AMOUNT)
    if amount > failure_limit:
        return False, "Payment declined by the simulator limit."
    return True, ""