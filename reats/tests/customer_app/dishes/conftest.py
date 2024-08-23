from typing import Iterator
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def mock_googlemaps_distance_matrix() -> Iterator:
    patcher = patch(
        "utils.distance_computer.google_map_client.distance_matrix",
        return_value={
            "destination_addresses": [
                "1 Rue André Lalande, 91000 Évry-Courcouronnes, France",
                "49 Rue de la Clairière, 91000 Évry-Courcouronnes, France",
                "52 Av. de la Commune de Paris, 91220 Brétigny-sur-Orge, France",
                "14 Rue Marie Roche, 91090 Lisses, France",
            ],
            "origin_addresses": ["1 Rue René Cassin, 91100 Corbeil-Essonnes, France"],
            "rows": [
                {
                    "elements": [
                        {
                            "distance": {"text": "9.2 km", "value": 9206},
                            "duration": {"text": "13 mins", "value": 800},
                            "status": "OK",
                        },
                        {
                            "distance": {"text": "12.0 km", "value": 11955},
                            "duration": {"text": "15 mins", "value": 886},
                            "status": "OK",
                        },
                        {
                            "distance": {"text": "22.0 km", "value": 21955},
                            "duration": {"text": "24 mins", "value": 1417},
                            "status": "OK",
                        },
                        {
                            "distance": {"text": "9.2 km", "value": 9160},
                            "duration": {"text": "13 mins", "value": 797},
                            "status": "OK",
                        },
                    ]
                }
            ],
        },
    )
    yield patcher.start()
    patcher.stop()
