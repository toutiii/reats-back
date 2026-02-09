"""Fixtures pour les tests du Dashboard Stats.

Utilise les fixtures JSON pré-chargées par django_db_setup dans le conftest.py global.
Les commandes pour cooker_id=1 sont déjà disponibles avec différents statuts.
"""

import pytest


@pytest.fixture
def dashboard_stats_path() -> str:
    """Path de l'endpoint dashboard stats."""
    return "/api/v1/cookers-dashboard/stats/"


@pytest.fixture
def popular_items_path() -> str:
    """Path de l'endpoint dashboard popular-items."""
    return "/api/v1/cookers-dashboard/popular-items/"


@pytest.fixture
def recent_reviews_path() -> str:
    """Path de l'endpoint dashboard recent-reviews."""
    return "/api/v1/cookers-dashboard/recent-reviews/"
