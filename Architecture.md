# Pulse Analytics — Architecture

## 1. Overview

Pulse Analytics utiliza una arquitectura backend basada en Django, con PostgreSQL como sistema de persistencia, Redis como infraestructura de caching y broker de mensajes, y Celery para ejecutar tareas asíncronas.

La aplicación expone una API GraphQL para interactuar con los datos y delega determinadas operaciones de procesamiento a workers independientes.

El objetivo de esta arquitectura es separar las solicitudes de los usuarios de las tareas que requieren procesamiento adicional, evitando que operaciones como la generación de reportes deban ejecutarse íntegramente durante una solicitud HTTP.

## 2. Componentes principales

### Django

Django es el núcleo de la aplicación y se encarga de:

- Exponer la API GraphQL.
- Gestionar la lógica de negocio.
- Interactuar con los modelos.
- Persistir eventos, reportes y alertas.
- Coordinar el inicio de tareas asíncronas.

### PostgreSQL

PostgreSQL funciona como sistema principal de persistencia.

Almacena las entidades utilizadas por la aplicación, incluyendo:

- Eventos registrados.
- Reportes generados.
- Alertas de anomalías.

La base de datos también permite aplicar restricciones de integridad para proteger la consistencia de los datos.

### Redis

Redis cumple dos responsabilidades:

- Broker de mensajes utilizado por Celery para distribuir tareas.
- Almacenamiento temporal para funcionalidades de caching.

Estas responsabilidades utilizan Redis como infraestructura compartida, pero representan usos diferentes dentro del sistema.

### Celery Worker

Los workers ejecutan las tareas asíncronas enviadas por Django.

Entre las operaciones delegadas se encuentran:

- Procesamiento de eventos.
- Generación y procesamiento de reportes.
- Exportación de información a CSV.
- Verificación de anomalías en las ventas.

### Celery Beat

Celery Beat se encarga de programar tareas periódicas.

Esto permite ejecutar determinadas operaciones automáticamente sin depender de una solicitud directa del usuario.

## 3. Flujo de procesamiento

### Ingesta de eventos

1. Un cliente realiza una solicitud a la API GraphQL.
2. Django procesa la operación y valida los datos recibidos según las validaciones implementadas.
3. Los eventos se almacenan en PostgreSQL.
4. Las operaciones que requieren procesamiento adicional pueden delegarse a Celery.

### Generación de reportes

1. El cliente solicita la creación de un reporte.
2. Django registra el reporte en PostgreSQL.
3. Una vez confirmada la transacción, se inicia el flujo de tareas asíncronas.
4. Celery ejecuta las tareas correspondientes.
5. Los resultados se procesan y se genera un archivo CSV.
6. El estado del reporte se actualiza según la lógica implementada.

### Detección de anomalías

1. Una tarea ejecuta la verificación de ventas.
2. Se consultan los datos necesarios en PostgreSQL.
3. Se evalúan las condiciones definidas para detectar anomalías.
4. Las alertas identificadas se almacenan en la base de datos.

La integridad de las alertas se complementa con restricciones de base de datos para evitar registros duplicados bajo concurrencia.

## 4. Comunicación entre componentes

| Origen | Destino | Responsabilidad |
|---|---|---|
| Cliente | Django | Solicitudes GraphQL |
| Django | PostgreSQL | Lectura y escritura de datos |
| Django | Redis | Acceso a caché y envío de tareas a Celery |
| Celery Worker | Redis | Consumo de tareas |
| Celery Worker | PostgreSQL | Procesamiento y actualización de datos |
| Celery Beat | Redis | Programación y envío de tareas |

## 5. Decisiones técnicas

### Procesamiento asíncrono

La generación de reportes y otras operaciones de procesamiento se delegan a Celery para desacoplarlas del ciclo de vida de una solicitud HTTP.

Esto permite que la API no tenga que esperar a que finalicen todas las operaciones de procesamiento.

### Uso de transaction.on_commit()

El inicio del flujo de generación de reportes se realiza después de confirmar la transacción de base de datos.

Esto evita que una tarea asíncrona intente acceder a un registro que todavía no fue confirmado por la transacción que lo creó.

### Integridad de datos bajo concurrencia

La detección de anomalías contempla posibles ejecuciones concurrentes.

Se utilizan restricciones de integridad en PostgreSQL para proteger la unicidad de las alertas, evitando depender exclusivamente de una comprobación previa en código de aplicación.

### Caching

Redis se utiliza para almacenar temporalmente información y reducir consultas repetidas.

La aplicación contempla la invalidación de caché cuando se modifican determinados datos.

## 6. Entorno de desarrollo

Docker Compose permite ejecutar los componentes principales del sistema de manera coordinada:

- Aplicación Django.
- PostgreSQL.
- Redis.
- Celery Worker.
- Celery Beat.

Cada servicio tiene una responsabilidad específica y se comunica con los demás mediante la configuración definida en Docker Compose.

## 7. Testing

El proyecto incluye pruebas automatizadas para funcionalidades de GraphQL y tareas asíncronas.

Las pruebas buscan verificar comportamientos importantes de la aplicación, incluyendo la lógica de procesamiento y la detección de anomalías.

La existencia de pruebas automatizadas no implica por sí sola cobertura completa del sistema.