import logging
from typing import Any

import googlemaps
from django.conf import settings
from django.db.models import QuerySet
from googlemaps.exceptions import ApiError, HTTPError, Timeout, TransportError

logger = logging.getLogger("watchtower-logger")
google_map_client = googlemaps.Client(key=settings.GOOGLE_API_KEY)


def compute_distance(
    origins: list[str],
    destinations: list[str],
) -> dict:
    """
    Compute the distance between two addresses

    :param origins: list of origin addresses
    :param destinations: list of destination addresses
    :return: dict containing the distance between addresses
    """
    try:
        distance_dict: dict[str, Any] = google_map_client.distance_matrix(
            origins=origins,
            destinations=destinations,
        )
    except (
        ApiError,
        TransportError,
        Timeout,
        HTTPError,
    ) as e:
        logger.error(e)
        distance_dict = {"status": "KO"}
        return distance_dict
    except Exception as e:
        logger.error(e)
        distance_dict = {"status": "KO"}
        return distance_dict

    return distance_dict


def get_closest_cookers_ids_from_customer_search_address(
    customer_address: str,
    cookers: QuerySet,
    search_radius: int,
) -> list:
    """
    Compute the distance from the customer address to the cookers addresses

    :param customer_address: str
    :param cookers_addresses: QuerySet
    :param search_radius: int (in KM)
    :return: dict containing closest cookers ids from the customer address
    """
    closest_cookers_ids: list[int] = []
    cookers_adresses_queryset: QuerySet = cookers.order_by("id").values_list(
        "street_number", "street_name", "address_complement", "postal_code", "town"
    )
    cookers_ids = cookers.order_by("id").values_list("id", flat=True)
    cookers_adresses = [
        f"{cooker[0]} {cooker[1]} {cooker[2]}, {cooker[3]} {cooker[4]}, {settings.DEFAULT_SEARCH_COUNTRY}"
        for cooker in cookers_adresses_queryset
    ]
    cookers_ids_addresses_dict: dict[int, str] = dict(
        zip(cookers_ids, cookers_adresses)
    )

    distance_dict: dict[str, Any] = compute_distance(
        origins=[customer_address + f", {settings.DEFAULT_SEARCH_COUNTRY}"],
        destinations=list(cookers_ids_addresses_dict.values()),
    )

    logger.debug(distance_dict)

    for cooker_id, distance in zip(
        cookers_ids_addresses_dict.keys(), distance_dict["rows"][0]["elements"]
    ):

        if distance["status"] != "OK":
            continue

        if float(distance["distance"]["value"]) <= float(search_radius * 1000):
            closest_cookers_ids.append(cooker_id)

    return closest_cookers_ids
