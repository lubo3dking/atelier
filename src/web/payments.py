"""One-time unlock payments via Stripe Checkout (optional, "sellable").

Freemium, deliberately accountless for the MVP: a device gets a few free tech
packs, then **one payment unlocks unlimited use forever** on that device. When
the free quota is spent the API asks the browser to complete a Stripe Checkout
session; on success Stripe redirects back with the session id, we verify it is
paid, mark the device unlocked (see `JobStore.unlock_device`), and mark the
session spent so it can't be reused.

Enabled only when ``STRIPE_SECRET_KEY`` is set; otherwise the app is FREE &
UNLIMITED (no paywall) so it runs out of the box locally. The `stripe` SDK is
imported lazily so neither the import nor offline tests need it.
"""
from __future__ import annotations

from typing import Any

from .. import config


def payments_enabled() -> bool:
    return bool(config.STRIPE_SECRET_KEY)


def _client() -> Any:
    import stripe  # lazy: only needed when payments are enabled

    stripe.api_key = config.STRIPE_SECRET_KEY
    return stripe


def create_checkout_session(success_url: str, cancel_url: str) -> dict[str, str]:
    """Create a Checkout session for the one-time unlock. Returns {id, url}."""
    stripe = _client()
    session = stripe.checkout.Session.create(
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
        line_items=[
            {
                "quantity": 1,
                "price_data": {
                    "currency": config.CURRENCY,
                    "unit_amount": config.UNLOCK_PRICE_CENTS,
                    "product_data": {
                        "name": f"{config.BRAND_NAME} — unlimited unlock",
                        "description": "One-time payment. Unlimited tech packs, forever.",
                    },
                },
            }
        ],
    )
    return {"id": session.id, "url": session.url}


def session_is_paid(session_id: str) -> bool:
    """Verify with Stripe that a Checkout session completed and was paid."""
    stripe = _client()
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception:  # noqa: BLE001 — unknown / malformed id -> not paid
        return False
    return getattr(session, "payment_status", None) == "paid"


def price_label() -> str:
    """Human price like '€29.00' / '$29.00' for the unlock, for the UI."""
    amount = config.UNLOCK_PRICE_CENTS / 100
    symbol = {"eur": "€", "usd": "$", "gbp": "£", "bgn": "лв "}.get(config.CURRENCY, "")
    return f"{symbol}{amount:.2f}".strip()
