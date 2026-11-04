from django.core.cache import cache
import pytest
from decimal import Decimal
from core.models import Reporte



@pytest.mark.django_db
def test_dashboard_stats_returns_correct_counts(graphql_client, event_factory):
    cache.delete('dashboard_stats')  # 👈 evitar contaminación entre tests
    
    event_factory(event_type='purchase_completed', payload={'amount': 100})
    event_factory(event_type='purchase_completed', payload={'amount': 200})
    event_factory(event_type='product_viewed', payload={})
    
    result = graphql_client.query('''
        query {
            dashboardStats {
                totalEvents
                totalPurchases
                totalViews
            }
        }
    ''')
    
    assert result.errors is None
    data = result.data['dashboardStats']
    assert data['totalEvents'] == 3
    assert data['totalPurchases'] == 2
    assert data['totalViews'] == 1
    
    
    
    
@pytest.mark.django_db(transaction=True)
def test_crear_reporte_dispara_pipeline_y_completada(graphql_client, event_factory):
    event_factory(event_type='purchase_completed', payload={'amount': 150.00})
    event_factory(event_type='product_viewed', payload={'product_id': 'abc'})
    
    result = graphql_client.query('''
        mutation {
            crearReporte(
                fechaDesde: "2026-01-01T00:00:00Z",
                fechaHasta: "2026-12-31T23:59:59Z"
            ) {
                id
                status
                reportType
            }
        }
    ''')
    
    assert result.errors is None
    data = result.data['crearReporte']
    assert data['status'] == 'pending'
    reporte_id = data['id']
    
    reporte = Reporte.objects.get(id=reporte_id)
    assert reporte.status == 'completed'
    assert reporte.result_data is not None
    assert 'ventas_totales' in reporte.result_data
    assert Decimal(reporte.result_data['ventas_totales']) == Decimal('150.00')
    assert reporte.result_data['vistas_totales'] == 1
    assert reporte.file_path is not None  

@pytest.mark.django_db(transaction=True)
def test_create_event_invalida_cache_dashboard(graphql_client, event_factory, settings):
    cache.delete('dashboard_stats')
    
    event_factory(event_type='product_viewed', payload={})

    result1 = graphql_client.query('''
        query { dashboardStats { totalEvents } }
    ''')
    assert result1.data['dashboardStats']['totalEvents'] == 1

    result2 = graphql_client.query('''
        mutation {
            createEvent(eventType: "purchase_completed", payload: { amount: 100 }) {
                id
                processed
            }
        }
    ''')
    assert result2.errors is None

    result3 = graphql_client.query('''
        query { dashboardStats { totalEvents totalPurchases } }
    ''')
    assert result3.data['dashboardStats']['totalEvents'] == 2
    assert result3.data['dashboardStats']['totalPurchases'] == 1