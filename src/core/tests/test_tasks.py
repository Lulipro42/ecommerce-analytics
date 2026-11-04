import pytest
from django.utils import timezone
from datetime import timedelta
from core.models import Event, Alerta
from core.tasks import verificar_alertas_ventas


def _crear_evento_con_timestamp(event_type, amount, hace):
    """Helper: crea un evento y le fuerza el timestamp a 'hace X tiempo atrás'."""
    ahora = timezone.now()
    evento = Event.objects.create(
        event_type=event_type,
        payload={'amount': amount},
    )
    Event.objects.filter(id=evento.id).update(timestamp=ahora - hace)
    return evento


@pytest.mark.django_db
def test_caida_de_ventas_crea_alerta_medium():
    # Arrange: hora anterior (hace 1h30 y 1h20) suma 900
    _crear_evento_con_timestamp('purchase_completed', 500, timedelta(hours=1, minutes=30))
    _crear_evento_con_timestamp('purchase_completed', 400, timedelta(hours=1, minutes=20))

    # Hora actual: 500 -> caída de (500-900)/900 = -44.4% (entre 20% y 49%, o sea medium)
    _crear_evento_con_timestamp('purchase_completed', 500, timedelta(minutes=20))

    # Act
    resultado = verificar_alertas_ventas.apply()

    # Assert
    assert "Alerta creada" in resultado.result

    alertas = Alerta.objects.filter(alert_type='sales_drop', resolved=False)
    assert alertas.count() == 1
    assert alertas.first().severity == 'medium'


@pytest.mark.django_db
def test_caida_de_ventas_severa_crea_alerta_high():
    # Arrange: hora anterior suma 900 (igual que el test anterior)
    _crear_evento_con_timestamp('purchase_completed', 500, timedelta(hours=1, minutes=30))
    _crear_evento_con_timestamp('purchase_completed', 400, timedelta(hours=1, minutes=20))

    # Hora actual: 200 -> caída de (200-900)/900 = -77.8% (>= 50%, o sea high)
    _crear_evento_con_timestamp('purchase_completed', 200, timedelta(minutes=20))

    # Act
    resultado = verificar_alertas_ventas.apply()

    # Assert
    assert "Alerta creada" in resultado.result

    alertas = Alerta.objects.filter(alert_type='sales_drop', resolved=False)
    assert alertas.count() == 1
    assert alertas.first().severity == 'high'


@pytest.mark.django_db
def test_sin_datos_historicos_no_crea_alerta():
    # Arrange: NO creamos nada en la ventana "hora anterior" (hace 2h a hace 1h)
    # Podemos crear algo en la hora actual, no debería importar
    _crear_evento_con_timestamp('purchase_completed', 100, timedelta(minutes=10))

    # Act
    resultado = verificar_alertas_ventas.apply()

    # Assert
    assert "Sin datos históricos" in resultado.result
    assert Alerta.objects.filter(resolved=False).count() == 0

@pytest.mark.django_db(transaction=True)
def test_no_duplica_alerta_si_ya_existe_una_abierta():
    # Arrange: ya existe una alerta abierta (creada "a mano", sin pasar por la task)
    Alerta.objects.create(
        alert_type='sales_drop',
        message='Alerta previa de prueba',
        severity='medium',
        resolved=False,
    )

    # Arrange: eventos que generarían OTRA caída de ventas (misma lógica del primer test)
    _crear_evento_con_timestamp('purchase_completed', 500, timedelta(hours=1, minutes=30))
    _crear_evento_con_timestamp('purchase_completed', 400, timedelta(hours=1, minutes=20))
    _crear_evento_con_timestamp('purchase_completed', 500, timedelta(minutes=20))

    # Act
    resultado = verificar_alertas_ventas.apply()

    # Assert
    assert "Alerta ya existe" in resultado.result
    # sigue habiendo 1 sola, no se creó una segunda
    assert Alerta.objects.filter(resolved=False).count() == 1


@pytest.mark.django_db
def test_ventas_se_recuperan_resuelve_alerta_existente():
    # Arrange: alerta existente sin resolver
    alerta = Alerta.objects.create(
        alert_type='sales_drop',
        message='Alerta previa de prueba',
        severity='medium',
        resolved=False,
    )

    # Arrange: ventas actuales >= ventas hora anterior (sin caída)
    _crear_evento_con_timestamp('purchase_completed', 500, timedelta(hours=1, minutes=30))
    _crear_evento_con_timestamp('purchase_completed', 400, timedelta(hours=1, minutes=20))
    _crear_evento_con_timestamp('purchase_completed', 1000, timedelta(minutes=20))

    # Act
    resultado = verificar_alertas_ventas.apply()

    # Assert
    alerta.refresh_from_db()
    assert alerta.resolved is True
    assert alerta.resolved_at is not None