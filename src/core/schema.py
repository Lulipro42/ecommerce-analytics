import strawberry
import strawberry_django
from strawberry import auto
from strawberry.scalars import JSON
from django.db import transaction
from django.core.cache import cache
from .models import Event, Reporte, Alerta
from .tasks import procesar_evento, ejecutar_pipeline_reporte


@strawberry_django.type(Event)
class EventType:
    id: auto
    event_type: auto
    payload: JSON
    timestamp: auto
    processed: auto


@strawberry.type
class DashboardStats:
    total_events: int
    total_purchases: int
    total_views: int
    events_by_type: list[str]


@strawberry_django.type(Reporte)
class ReporteType:
    id: auto
    report_type: auto
    parameters: JSON
    status: auto
    result_data: JSON
    created_at: auto
    completed_at: auto


@strawberry_django.type(Alerta)
class AlertaType:
    id: auto
    alert_type: auto
    message: auto
    severity: auto
    resolved: auto
    created_at: auto
    resolved_at: auto


@strawberry.type
class Query:
    @strawberry.field
    def events(self, limit: int = 50, offset: int = 0) -> list[EventType]:
        return Event.objects.all()[offset : offset + limit]

    @strawberry.field
    def dashboard_stats(self) -> DashboardStats:
        cached = cache.get('dashboard_stats')
        if cached:
            return DashboardStats(**cached)

        stats = {
            'total_events': Event.objects.count(),
            'total_purchases': Event.objects.filter(event_type='purchase_completed').count(),
            'total_views': Event.objects.filter(event_type='product_viewed').count(),
            'events_by_type': list(Event.objects.values_list('event_type', flat=True).distinct()),
        }

        cache.set('dashboard_stats', stats, 300)
        return DashboardStats(**stats)

    @strawberry.field
    def reportes(self) -> list[ReporteType]:
        return Reporte.objects.all().order_by('-created_at')

    @strawberry.field
    def alertas(self, solo_activas: bool = False) -> list[AlertaType]:
        qs = Alerta.objects.all().order_by('-created_at')
        if solo_activas:
            qs = qs.filter(resolved=False)
        return qs


@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_event(self, event_type: str, payload: JSON) -> EventType:
        with transaction.atomic():
            event = Event.objects.create(
                event_type=event_type,
                payload=payload
            )
            transaction.on_commit(
                lambda: procesar_evento.delay(event.id)
            )
        return event

    @strawberry.mutation
    def crear_reporte(self, fecha_desde: str, fecha_hasta: str) -> ReporteType:
        with transaction.atomic():
            reporte = Reporte.objects.create(
                report_type='monthly_sales',
                parameters={
                    'fecha_desde': fecha_desde,
                    'fecha_hasta': fecha_hasta,
                },
                status='pending',
            )

            transaction.on_commit(
                lambda: ejecutar_pipeline_reporte(
                    reporte_id=reporte_id,
                    fecha_desde=fecha_desde,
                    fecha_hasta=fecha_hasta,
                )
            )
            return reporte


schema = strawberry.Schema(query=Query, mutation=Mutation)