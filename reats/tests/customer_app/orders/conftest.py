from typing import Iterator
from unittest.mock import patch

import pytest


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
