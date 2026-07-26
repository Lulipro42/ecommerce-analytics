import pytest
from strawberry_django.test.client import TestClient
from core.models import Event, Reporte


@pytest.fixture
def graphql_client(db):
    """Cliente de GraphQL para tests de integración (ejecuta contra el endpoint real)."""
    return TestClient("/graphql/")


@pytest.fixture
def event_factory(db):
    """Factory simple para crear eventos de prueba."""
    def _factory(event_type='product_viewed', payload=None, processed=False):
        return Event.objects.create(
            event_type=event_type,
            payload=payload or {},
            processed=processed,
        )
    return _factory


@pytest.fixture
def reporte_factory(db):
    """Factory para crear reportes de prueba."""
    def _factory(status='pending', parameters=None):
        return Reporte.objects.create(
            report_type='monthly_sales',
            parameters=parameters or {},
            status=status,
        )
    return _factory


@pytest.fixture(autouse=True)
def clear_cache():
    from django.core.cache import cache
    cache.clear()