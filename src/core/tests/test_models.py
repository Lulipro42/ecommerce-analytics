import pytest
from core.models import Event, Reporte, Alerta


@pytest.mark.django_db
def test_event_str_representation():
    evento = Event.objects.create(event_type='purchase_completed', payload={})
    assert 'purchase_completed' in str(evento)


@pytest.mark.django_db
def test_event_payload_default_es_dict_vacio():
    evento = Event.objects.create(event_type='product_viewed')
    assert evento.payload == {}


@pytest.mark.django_db
def test_alerta_str_representation():
    alerta = Alerta.objects.create(
        alert_type='sales_drop', message='test', severity='high'
    )
    assert 'sales_drop' in str(alerta)
    assert 'high' in str(alerta)


@pytest.mark.django_db
def test_reporte_status_default_es_pending():
    reporte = Reporte.objects.create(report_type='monthly_sales', parameters={})
    assert reporte.status == 'pending'