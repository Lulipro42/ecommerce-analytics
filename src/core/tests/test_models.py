import pytest
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.test import TransactionTestCase
from django.db import connection
from decimal import Decimal

from core.models import Event, Reporte, Alerta


# ========== TESTS ORIGINALES ==========

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


# ========== TEST DE CONCURRENCIA NUEVO ==========

class EventosConcurrenciaTest(TransactionTestCase):
    """
    Test de concurrencia: múltiples threads crean eventos simultáneamente.
    Verifica que no se pierdan eventos ni haya errores de integridad.
    """

    def _crear_evento(self, event_type, amount):
        """Helper que crea un evento y devuelve su ID."""
        evento = Event.objects.create(
            event_type=event_type,
            payload={'amount': str(amount)},
        )
        return evento.id

    def test_crear_eventos_concurrentes(self):
        """
        20 threads crean eventos de compra simultáneamente.
        Verifica que todos se creen y el conteo sea correcto.
        """
        num_eventos = 20
        monto = Decimal('100.00')

        tareas = [
            ('purchase_completed', monto)
            for _ in range(num_eventos)
        ]

        eventos_creados = []
        errores = []

        with ThreadPoolExecutor(max_workers=20) as executor:
            futuros = {
                executor.submit(self._crear_evento, tipo, monto): i
                for i, (tipo, monto) in enumerate(tareas)
            }

            for futuro in as_completed(futuros):
                try:
                    evento_id = futuro.result(timeout=10)
                    eventos_creados.append(evento_id)
                except Exception as e:
                    errores.append(str(e))

        # Cerrar conexiones de los hilos
        connection.close()

        # ASSERT 1: No hay errores
        self.assertEqual(len(errores), 0, f"Errores encontrados: {errores}")

        # ASSERT 2: Se crearon todos los eventos
        self.assertEqual(len(eventos_creados), num_eventos)

        # ASSERT 3: El conteo en DB es correcto
        self.assertEqual(Event.objects.filter(event_type='purchase_completed').count(), num_eventos)

        # ASSERT 4: Cada evento tiene un ID único (no hay duplicados)
        self.assertEqual(len(set(eventos_creados)), num_eventos)