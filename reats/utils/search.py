import re

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db.models import QuerySet

from utils.enums import SearchWeightEnum


def sanitize_search_term(term: str) -> str:
    """
    Sanitizes the search term to remove characters that could break PostgreSQL raw tsquery.
    """
    if not term:
        return ""
    # Remove characters that have special meaning in raw tsquery: ! & | ( ) : *
    return re.sub(r"[!&|():*]", "", term).strip()


def _build_prefix_tsquery(term: str) -> str:
    """
    Converts a search term into a prefix tsquery string.
    Each word gets a ':*' suffix so that partial matches work.
    Example: "pou bra" -> "pou:* & bra:*"
    """
    sanitized = sanitize_search_term(term)
    words = [w.strip() for w in sanitized.split() if w.strip()]
    if not words:
        return ""
    return " & ".join(f"{w}:*" for w in words)


def apply_fulltext_search(
    queryset: QuerySet, term: str, ranked_fields: list[tuple[str, SearchWeightEnum]], min_rank: float = 0.01
) -> QuerySet:
    """
    Applies PostgreSQL full-text search with prefix matching and ranking.

    Args:
        queryset: The base QuerySet.
        term: The search term (supports partial words).
        ranked_fields: List of (field_name, SearchWeightEnum) tuples.
        min_rank: Minimum rank threshold.

    Returns:
        Filtered and ranked QuerySet.
    """
    if not term:
        return queryset

    tsquery_str = _build_prefix_tsquery(term)
    if not tsquery_str:
        return queryset

    query = SearchQuery(tsquery_str, search_type="raw", config="simple")

    vector = None
    for field, weight in ranked_fields:
        v = SearchVector(field, weight=weight.value, config="simple")
        vector = v if vector is None else vector + v

    if vector is None:
        return queryset

    return (
        queryset.annotate(search_rank=SearchRank(vector, query))
        .filter(search_rank__gte=min_rank)
        .order_by("-search_rank")
    )
