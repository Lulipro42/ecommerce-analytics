# Pulse Analytics

Dashboard de analytics e-commerce con procesamiento de eventos en tiempo real, reportes generados en background y alertas automáticas de anomalías.

> **Estado:** MVP funcional — Semanas 1-6 completadas. Deploy planeado para Semana 7.

---

## Qué resuelve

Los e-commerce generan miles de eventos diarios (vistas, carritos, compras). Sin un sistema centralizado, responder preguntas como "cuánto vendí esta hora?" o "por qué cayeron las ventas?" requiere queries manuales y tiempo.

Pulse Analytics ingesta eventos vía GraphQL, los procesa asincrónicamente con Celery, cachea agregaciones en Redis y detecta caídas de ventas automáticamente.

---

## Arquitectura

```
┌─────────────┐     GraphQL      ┌─────────────┐
│   Cliente   │ ◄──────────────► │    Django   │
│  (React/    │    (Strawberry)  │   (Gunicorn)│
│  Playground)│                  │             │
└─────────────┘                  └──────┬──────┘
                                         │
                  ┌──────────────────────┼──────────────────────┐
                  │                      │                      │
                  ▼                      ▼                      ▼
            ┌──────────┐           ┌──────────┐           ┌──────────┐
            │PostgreSQL│           │  Redis   │           │  Celery  │
            │  (datos) │           │ (cache + │           │ (workers │
            │          │           │  broker) │           │  + beat) │
            └──────────┘           └──────────┘           └──────────┘
```

### Flujo de un evento

Usuario compra → Mutation `createEvent` → Event guardado en PostgreSQL → Transaction commit → Celery task `procesar_evento` → Marca `processed=true` → Invalida cache Redis

### Flujo de un reporte

Mutation `crearReporte` → Reporte creado (`status=pending`) → Transaction commit → Celery chain `ejecutar_pipeline_reporte` → `extraer_datos` → `agregar_datos` → `generar_csv` → `notificar_reporte_listo` → Reporte actualizado (`status=completed`, `result_data=JSON`)

### Flujo de alertas

Celery Beat cada 5min → `verificar_alertas_ventas()` → SUM(ventas hora actual) vs SUM(ventas hora anterior) → Caída >= 20% → Crear Alerta (`severity=medium/high`) / Caída < 20% → Resolver alertas abiertas

---

## Stack y decisiones

| Tecnología | Problema que resuelve | Alternativa rechazada | Por qué |
|---|---|---|---|
| Strawberry GraphQL | Frontend pide exactamente lo que necesita; un solo endpoint tipado | Django REST Framework | Over-fetching en REST; más endpoints que mantener |
| Celery + Redis | Procesamiento async sin bloquear requests; scheduling de tareas | RQ | RQ no soporta chains ni Beat nativo |
| PostgreSQL JSONB | Payload flexible sin migraciones por cada nuevo campo de evento | Campos fijos + migraciones | Los eventos cambian; el schema no debe cambiar con ellos |
| Docker Compose | Entorno idéntico en local, CI y producción | Instalación nativa | "Funciona en mi máquina" → no existe |
| pytest + CI GitHub | Tests automáticos en cada push | `python manage.py test` | pytest tiene fixtures, parametrización, mejor output |

---

## Features implementadas

- [x] Mutation `createEvent` — crea evento y dispara procesamiento async
- [x] Task `procesar_evento` — marca como procesado, invalida cache
- [x] Query `events` — lista todos los eventos
- [x] Query `dashboardStats` — agregaciones cacheadas en Redis (TTL 5min)
- [x] Invalidación automática de cache al crear nuevos eventos
- [x] Mutation `crearReporte` — solicita reporte con rango de fechas
- [x] Pipeline Celery (chain): extraer → agregar → generar_csv → notificar
- [x] Estados del reporte: `pending → processing → completed`
- [x] Query `reportes` — historial con resultados agregados
- [x] Celery Beat cada 5 minutos
- [x] Detección automática de caída de ventas >= 20%
- [x] Deduplicación: no crea alerta duplicada si ya existe una abierta
- [x] Resolución automática cuando las ventas se estabilizan
- [x] Query `alertas(soloActivas: true)` — dashboard de alertas
- [x] Tests de integración con pytest (3/3 pasando)
- [x] CI/CD con GitHub Actions
- [x] Docker Compose con 5 servicios

---

## Demo

### Query: Dashboard de estadísticas

```graphql
query {
  dashboardStats {
    totalEvents
    totalPurchases
    totalViews
    eventsByType
  }
}
```

### Mutation: Crear evento de compra

```graphql
mutation {
  createEvent(
    eventType: "purchase_completed",
    payload: { amount: 150.00, product_id: "abc-123" }
  ) {
    id
    eventType
    processed
  }
}
```

### Mutation: Solicitar reporte mensual

```graphql
mutation {
  crearReporte(
    fechaDesde: "2026-07-01T00:00:00Z",
    fechaHasta: "2026-07-31T23:59:59Z"
  ) {
    id
    status
    reportType
  }
}
```

### Query: Ver alertas activas

```graphql
query {
  alertas(soloActivas: true) {
    id
    message
    severity
    createdAt
  }
}
```

---

## Setup local

```bash
# 1. Clonar
git clone https://github.com/tu-usuario/pulse-analytics.git
cd pulse-analytics

# 2. Variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# 3. Levantar servicios
docker compose up -d

# 4. Migraciones
docker compose exec web python manage.py migrate

# 5. Crear superuser (opcional)
docker compose exec web python manage.py createsuperuser

# 6. GraphQL Playground
open http://localhost:8001/graphql/
```

## Correr tests

```bash
docker compose exec web pytest core/tests/ -v
```

## Testing

| Test | Qué valida | Estado |
|---|---|---|
| `test_dashboard_stats_returns_correct_counts` | Query de agregaciones con datos de prueba | Pass |
| `test_crear_reporte_dispara_pipeline_y_completa` | Mutation + pipeline Celery end-to-end | Pass |
| `test_create_event_invalida_cache_dashboard` | Cache invalidado al crear evento | Pass |

CI: GitHub Actions corre tests automáticamente en cada push a `main`/`develop` y en cada PR a `main`.

---

## Roadmap

| Semana | Tarea | Estado |
|---|---|---|
| 1-3 | Setup, modelos, schema GraphQL básico | Completado |
| 4 | Pipeline de reportes con Celery chain | Completado |
| 5 | Celery Beat + alertas automáticas | Completado |
| 6 | Tests + CI/CD + README profesional | Completado |
| 7 | Deploy en Railway/Render + monitoreo | Pendiente |
| 8 | Optimización: índices PostgreSQL, rate limiting | Planificado |

---

## Decisiones técnicas

### ¿Por qué GraphQL y no REST?

En REST, para mostrar "stats del dashboard + últimos eventos + alertas activas" necesitás 3 requests. En GraphQL, 1 request con 3 campos. Menos overhead de red, menos código de frontend.

### ¿Por qué Celery chain y no una sola task grande?

Separar extraer → agregar → generar permite:
- Retry individual por paso (si falla la agregación, no re-extraigo)
- Reutilizar `agregar_datos` para otros tipos de reporte
- Monitoreo granular (veo qué paso falla)

### ¿Por qué `Cast` + `KeyTextTransform` para `SUM(payload->>'amount')`?

`Sum('payload__amount')` directo sobre un `JSONField` falla: Postgres genera `SUM(jsonb)`, y esa función no existe — la tarea explotaba con una excepción no capturada y nunca llegaba a crear alertas.

La solución fue extraer el valor como texto con `KeyTextTransform('amount', 'payload')` y castearlo explícitamente a `DecimalField` antes de sumar, todo dentro del ORM. Esto evita SQL crudo, nombres de tabla hardcodeados, y mantiene la query portable entre backends.

---

## Licencia

MIT — Libre para uso y modificación.

---

## Deuda técnica conocida

1. **Tests de Celery en modo eager:** Los tests usan `CELERY_TASK_ALWAYS_EAGER=True`, 
   lo que ejecuta las tareas síncronamente. En producción, las tareas corren en workers 
   separados. Para testear el comportamiento real async, se necesitaría `pytest-celery` 
   o un entorno de integración.

2. **Cache invalidation en test:** El test de invalidación de cache pasa porque Celery 
   es eager. En producción, hay un delay entre `createEvent` y `procesar_evento` que 
   invalida el cache.

3. **Nombre de función `generar_csv`:** Originalmente guardaba JSON, no CSV. 
   Corregido en [fecha].