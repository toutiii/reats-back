import json
from typing import Iterator
from unittest.mock import patch

import pytest
import stripe
import stripe.util


@pytest.fixture
def mock_stripe_customer_create() -> Iterator:
    patcher = patch(
        "stripe.Customer.create",
        return_value={"id": "cus_QwIHcNB1jkYFwv"},
    )
    yield patcher.start()
    patcher.stop()


@pytest.fixture
def mock_stripe_customer_delete() -> Iterator:
    patcher = patch(
        "stripe.Customer.delete",
        return_value=stripe.util.convert_to_dict(  # ty: ignore[unresolved-attribute]
            json.loads(
                """{
                "deleted": true,
                "id": "cus_QyZ76Ae0W5KeqP",
                "object": "customer"
            }"""
            )
        ),
    )
    yield patcher.start()
    patcher.stop()
