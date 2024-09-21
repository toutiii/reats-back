def get_distance_ratio(distance: float) -> float:
    """
    For a given distance, compute the ratio which will be used to compute the delivery feels.

    :param distance: The distance in meters
    :return: The ratio
    """

    # TODO: Find the right values for the distance ratio, the values below are just placeholders

    if 0 < distance <= 2000:
        return 1.0

    elif 2001 < distance <= 4000:
        return 1.1

    elif 4001 < distance <= 6000:
        return 1.2

    elif 6001 < distance <= 8000:
        return 1.3

    elif 8001 < distance <= 10000:
        return 1.4

    elif distance > 10000:
        return 1.5

    else:
        raise ValueError("The distance must be greater than 0")
