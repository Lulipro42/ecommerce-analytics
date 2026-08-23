from celery import shared_task, chain
from celery.exceptions import MaxRetriesExceededError
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Sum, DecimalField
from django.db.models.functions import Cast
from django.db.models.fields.json import KeyTextTransform
from .models import Event, Reporte, Alerta
import logging
from datetime import timedelta
import csv
import io
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def procesar_evento(self, event_id):
    try:
        event = Event.objects.get(id=event_id)
        event.processed = True
        event.save()
        cache.delete('dashboard_stats')
        logger.info(f"Evento {event_id} procesado")
        return f"Evento {event_id} procesado"
    except Event.DoesNotExist:
        logger.warning(f"Evento {event_id} no existe, reintentando...")
        raise self.retry(countdown=2 ** self.request.retries)  # backoff: 1, 2, 4 seg
    except Exception as exc:
        logger.error(f"Error procesando evento {event_id}: {exc}")
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def extraer_datos(self, reporte_id, fecha_desde, fecha_hasta):
    try:
        reporte = Reporte.objects.get(id=reporte_id)
        reporte.status = 'processing'
        reporte.save()
        
        eventos = Event.objects.filter(
            timestamp__gte=fecha_desde,
            timestamp__lte=fecha_hasta
        )
        
        total = eventos.count()
        if total == 0:
            logger.warning(f"Reporte {reporte_id}: 0 eventos en el rango")
        
        return {
            'reporte_id': reporte_id,
            'eventos_ids': list(eventos.values_list('id', flat=True)),
            'total_eventos': total,
        }
    except Reporte.DoesNotExist:
        raise self.retry(countdown=2 ** self.request.retries)
    except Exception as exc:
        logger.error(f"Error en extraer_datos para {reporte_id}: {exc}")
        raise


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def agregar_datos(self, datos):
    try:
        reporte_id = datos['reporte_id']
        eventos_ids = datos['eventos_ids']
    
        eventos = Event.objects.filter(id__in=eventos_ids)
    
        ventas_monto = eventos.filter(event_type='purchase').aggregate(total=Sum(
            Cast(
                KeyTextTransform('amount', 'payload'),
                output_field=DecimalField(max_digits=12, decimal_places=2)
                )
            )
        )['total'] or 0

        vistas_count = eventos.filter(event_type='product_viewed').count()

        return {
            'reporte_id': reporte_id,
            'ventas_totales': ventas_monto,  # ← Ahora es monto, no count
            'vistas_totales': vistas_count,
            'total_eventos': datos['total_eventos'],
            }
    except Exception as exec:
        logger.error(f"Error en agregar datos: {exec}")
        raise self.retry(exec=exec)

@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def generar_csv(self, datos_agregados):
    try:
        reporte_id = datos_agregados['reporte_id']
        reporte = Reporte.objects.get(id=reporte_id)
        
        oupot = io.StringIO()
        writer = csv.writer(oupot)
        
        writer.writerow(['metrica', 'valor'])
        writer.writerow(['ventas_totales', datos_agregados['ventas_totales']])
        writer.writerow(['vistas_totales', datos_agregados['vistas_totales']])
        writer.writerow(['total_eventos', datos_agregados['total_eventos']])

        filename = f"reporte_{reporte_id}.csv"
        path = default_storage.save(f"reportes/{filename}", ContentFile(oupot.getvalue()))

        reporte.file_path = path
        reporte.result_data = datos_agregados
        reporte.status = 'completed'
        reporte.completed_at = timezone.now()
        reporte.save()

        return {
            'reporte_id':reporte_id,
            'mensaje': f"Reporte: {reporte_id} completado",
        }
    except Exception as exec:
        logger.error(f"Error en generar csv: {exec}")
        raise self.retr(exec=exec)


@shared_task
def notificar_reporte_listo(resultado):
    """
    resultado: dict con 'reporte_id' y 'mensaje' (viene de generar_csv)
    """
    reporte_id = resultado.get('reporte_id', 'unknown')
    mensaje = resultado.get('mensaje', 'sin mensaje')
    logger.info(f"✅ {mensaje}")
    return f"Notificación enviada para reporte {reporte_id}"

def ejecutar_pipeline_reporte(reporte_id, fecha_desde, fecha_hasta):
    pipeline = chain(
        extraer_datos.s(reporte_id, fecha_desde, fecha_hasta),
        agregar_datos.s(),
        generar_csv.s(),
        notificar_reporte_listo.s(),  # sin argumentos extra
    )
    return pipeline.apply_async()


def _sum_payload_amount(event_type, timestamp_gte, timestamp_lt):
    """
    Suma payload->>'amount' casteando a Decimal vía el ORM.

    OJO: el bug original era usar Sum('payload__amount') directo sobre un
    JSONField. Eso genera SUM(payload -> 'amount') en Postgres, que es de
    tipo jsonb, y Postgres no tiene una función SUM(jsonb) -> la tarea
    fallaba con una excepción no capturada y nunca llegaba a crear alertas.

    La solución: extraer el valor como texto (KeyTextTransform) y castearlo
    explícitamente a DecimalField antes de sumar, todo dentro del ORM
    (portable entre backends, sin SQL crudo ni nombres de tabla hardcodeados).
    """
    total = Event.objects.filter(
        event_type=event_type,
        timestamp__gte=timestamp_gte,
        timestamp__lt=timestamp_lt,
    ).aggregate(
        total=Sum(
            Cast(
                KeyTextTransform('amount', 'payload'),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )
    )['total']
    return total or 0


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def verificar_alertas_ventas(self):
    try:
        ahora = timezone.now()

        hora_actual_inicio = ahora - timedelta(hours=1)
        ventas_actual = _sum_payload_amount(
            'purchase_completed',
            hora_actual_inicio,
            ahora,
        )

        hora_anterior_inicio = ahora - timedelta(hours=2)
        hora_anterior_fin = ahora - timedelta(hours=1)
        ventas_anterior = _sum_payload_amount(
            'purchase_completed',
            hora_anterior_inicio,
            hora_anterior_fin,
        )

        # Evitar falsos positivos si no hay datos históricos
        if ventas_anterior == 0:
            _resolver_alertas_si_existen()
            return "Sin datos históricos, sin alerta"

        cambio = (ventas_actual - ventas_anterior) / ventas_anterior

        if cambio <= -0.20:
            # Evitar duplicados
            if not Alerta.objects.filter(alert_type='sales_drop', resolved=False).exists():
                Alerta.objects.create(
                    alert_type='sales_drop',
                    message=f"Ventas cayeron {abs(cambio):.1%} (de ${ventas_anterior:.2f} a ${ventas_actual:.2f})",
                    severity='high' if cambio <= -0.50 else 'medium',
                )
                return f"Alerta creada: caída {cambio:.1%}"
            return "Alerta ya existe"

        _resolver_alertas_si_existen()
        return f"Sin alerta ({cambio:+.1%})"
    except Exception as exc:
        logger.error(f"Error en verificar_alertas_ventas: {exc}")
        raise self.retry(exc=exc)


def _resolver_alertas_si_existen():
    Alerta.objects.filter(alert_type='sales_drop', resolved=False).update(
        resolved=True,
        resolved_at=timezone.now(),
    )