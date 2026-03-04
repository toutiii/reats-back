from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import QuerySet


def apply_trigram_search(
    queryset: QuerySet,
    term: str,
    fields: list[tuple[str, float]],
    sim_threshold: float = 0.1,
) -> QuerySet:
    """
    Applies PostgreSQL trigram similarity search across multiple fields with weights.

    Args:
        queryset: The base QuerySet.
        term: The search term.
        fields: List of (field_name, weight) tuples. Higher weight = more priority.
                Example: [("name", 1.0), ("description", 0.4)]
        sim_threshold: Minimum weighted similarity threshold (0 to 1).

    Returns:
        Filtered and ranked QuerySet.
    """
    term = (term or "").strip()
    if not term:
        return queryset

    similarity = None
    for field, weight in fields:
        sim = TrigramSimilarity(field, term) * weight
        similarity = sim if similarity is None else similarity + sim

    if similarity is None:
        return queryset

    return queryset.annotate(search_rank=similarity).filter(search_rank__gte=sim_threshold).order_by("-search_rank")
