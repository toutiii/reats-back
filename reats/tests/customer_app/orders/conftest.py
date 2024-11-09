import json
from typing import Iterator
from unittest.mock import patch

import pytest
import stripe


@pytest.fixture(autouse=True)
def mock_googlemaps_distance_matrix() -> Iterator:
    patcher = patch(
        "utils.distance_computer.google_map_client.distance_matrix",
        return_value={
            "destination_addresses": [
                "1 Rue André Lalande, 91000 Évry-Courcouronnes, " "France"
            ],
            "origin_addresses": [
                "13 Rue des Mazières, 91000 Évry-Courcouronnes, France"
            ],
            "rows": [
                {
                    "elements": [
                        {
                            "distance": {"text": "1.4 km", "value": 1390},
                            "duration": {"text": "5 mins", "value": 325},
                            "status": "OK",
                        }
                    ]
                }
            ],
            "status": "OK",
        },
    )
    yield patcher.start()
    patcher.stop()


@pytest.fixture
def mock_stripe_payment_intent_create() -> Iterator:
    patcher = patch(
        "stripe.PaymentIntent.create",
        return_value=stripe.util.convert_to_dict(
            json.loads(
                """{
                "amount": 150870,
                "amount_capturable": 0,
                "amount_details": {"tip": {}},
                "amount_received": 0,
                "application": null,
                "application_fee_amount": null,
                "automatic_payment_methods": {
                    "allow_redirects": "always",
                    "enabled": true
                },
                "canceled_at": null,
                "cancellation_reason": null,
                "capture_method": "automatic_async",
                "client_secret": "pi_3Q6VU7EEYeaFww1W0xCZEUxw_secret_OJqlWW9QRZZuSmAwUBklpxUf4",
                "confirmation_method": "automatic",
                "created": 1728125115,
                "currency": "eur",
                "customer": "cus_QyZ76Ae0W5KeqP",
                "description": null,
                "id": "pi_3Q6VU7EEYeaFww1W0xCZEUxw",
                "invoice": null,
                "last_payment_error": null,
                "latest_charge": null,
                "livemode": false,
                "metadata": {},
                "next_action": null,
                "object": "payment_intent",
                "on_behalf_of": null,
                "payment_method": null,
                "payment_method_configuration_details": null,
                "payment_method_options": {
                    "card": {
                        "installments": null,
                        "mandate_options": null,
                        "network": null,
                        "request_three_d_secure": "automatic"
                    }
                },
                "payment_method_types": ["card"],
                "processing": null,
                "receipt_email": null,
                "review": null,
                "setup_future_usage": null,
                "shipping": null,
                "source": null,
                "statement_descriptor": null,
                "statement_descriptor_suffix": null,
                "status": "requires_payment_method",
                "transfer_data": null,
                "transfer_group": null
            }"""
            )
        ),
    )
    yield patcher.start()
    patcher.stop()


@pytest.fixture
def mock_stripe_payment_intent_update() -> Iterator:
    patcher = patch("stripe.PaymentIntent.modify", return_value=None)
    yield patcher.start()
    patcher.stop()


@pytest.fixture
def mock_stripe_create_ephemeral_key() -> Iterator:
    patcher = patch(
        "stripe.EphemeralKey.create",
        return_value=stripe.util.convert_to_dict(
            json.loads(
                """{
                "associated_objects": [
                    {
                    "id": "cus_QyZ76Ae0W5KeqP",
                    "type": "customer"
                    }
                ],
                "created": 1728745953,
                "expires": 1728749553,
                "id": "ephkey_1Q96zdEEYeaFww1WqdVzrVXX",
                "livemode": false,
                "object": "ephemeral_key",
                "secret": "ek_test_YWNjdF8xUTN6bTZFRVllYUZ3dzFXLGwwb3VMVEZnT0ljSUw0Q0xYNm5rWGlMYTExYXRhVm4_00uVE9aZDp"
                }
                """
            )
        ),
    )
    yield patcher.start()
    patcher.stop()


@pytest.fixture
def stripe_payment_intent_success_webhook_data() -> dict:
    return {
        "id": "evt_3QJJlHEEYeaFww1W0AkpYuqj",
        "object": "event",
        "api_version": "2024-06-20",
        "created": 1731178320,
        "data": {
            "object": {
                "id": "pi_3Q6VU7EEYeaFww1W0xCZEUxw",
                "object": "payment_intent",
                "amount": 2313,
                "amount_capturable": 0,
                "amount_details": {"tip": {}},
                "amount_received": 2313,
                "application": None,
                "application_fee_amount": None,
                "automatic_payment_methods": {
                    "allow_redirects": "always",
                    "enabled": True,
                },
                "canceled_at": None,
                "cancellation_reason": None,
                "capture_method": "automatic_async",
                "client_secret": "pi_3Q6VU7EEYeaFww1W0xCZEUxw_secret_OJqlWW9QRZZuSmAwUBklpxUf4",
                "confirmation_method": "automatic",
                "created": 1731178315,
                "currency": "eur",
                "customer": "cus_QyZ76Ae0W5KeqP",
                "description": None,
                "invoice": None,
                "last_payment_error": None,
                "latest_charge": "ch_3QJJlHEEYeaFww1W0GkaBZRx",
                "livemode": False,
                "metadata": {},
                "next_action": None,
                "on_behalf_of": None,
                "payment_method": "pm_1QJIFdEEYeaFww1Wv5PfwHlU",
                "payment_method_configuration_details": {
                    "id": "pmc_1QJHuCEEYeaFww1WIyoetNa8",
                    "parent": None,
                },
                "payment_method_options": {
                    "card": {
                        "installments": None,
                        "mandate_options": None,
                        "network": None,
                        "request_three_d_secure": "automatic",
                    }
                },
                "payment_method_types": ["card"],
                "processing": None,
                "receipt_email": None,
                "review": None,
                "setup_future_usage": None,
                "shipping": None,
                "source": None,
                "statement_descriptor": None,
                "statement_descriptor_suffix": None,
                "status": "succeeded",
                "transfer_data": None,
                "transfer_group": None,
            }
        },
        "livemode": False,
        "pending_webhooks": 3,
        "request": {
            "id": "req_Q50llYH7NrdKeN",
            "idempotency_key": "359d36f4-80a2-4138-bd2d-0846239a6cc4",
        },
        "type": "payment_intent.succeeded",
    }


@pytest.fixture
def mock_stripe_webhook_construct_event_success(
    stripe_payment_intent_success_webhook_data: dict,
) -> Iterator:
    pather = patch(
        "stripe.Webhook.construct_event",
        return_value=stripe.util.convert_to_dict(
            stripe_payment_intent_success_webhook_data
        ),
    )
    yield pather.start()
    pather.stop()


@pytest.fixture
def mock_stripe_webhook_construct_event_failed() -> Iterator:
    patcher = patch(
        "stripe.Webhook.construct_event",
        side_effect=stripe.error.SignatureVerificationError("error", "sig_header"),
    )
    yield patcher.start()
    patcher.stop()
