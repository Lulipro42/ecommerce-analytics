# Pulse Analytics

Backend de analytics para e-commerce desarrollado con Django y GraphQL. Permite registrar eventos de actividad, procesarlos de forma asíncrona, generar reportes CSV y detectar anomalías en las ventas.

El proyecto explora el uso de procesamiento en segundo plano, tareas distribuidas, almacenamiento relacional, caching y coordinación entre componentes backend.

## Características principales

- **Ingesta de eventos:** recepción y consulta de eventos mediante una API GraphQL.
- **Procesamiento asíncrono:** ejecución de tareas en segundo plano utilizando Celery.
- **Generación de reportes:** procesamiento de datos y exportación de reportes en formato CSV.
- **Detección de anomalías:** identificación de posibles anomalías en las ventas.
- **Caching:** utilización de Redis para almacenar información temporal y gestionar la invalidación de caché.
- **Tareas periódicas:** programación de tareas mediante Celery Beat.
- **Testing:** pruebas automatizadas para funcionalidades de GraphQL y tareas asíncronas.

## Stack tecnológico

| Tecnología | Uso |
|---|---|
| Python | Lenguaje principal |
| Django | Framework backend |
| GraphQL | API de consulta e ingesta |
| PostgreSQL | Base de datos relacional |
| Redis | Broker de Celery y caching |
| Celery | Procesamiento asíncrono |
| Celery Beat | Programación de tareas |
| Docker Compose | Entorno de desarrollo |
| pytest | Pruebas automatizadas |

## Arquitectura general

El sistema utiliza una arquitectura backend basada en Django. GraphQL funciona como interfaz de acceso a los datos, mientras que Celery permite ejecutar tareas que no necesitan completarse durante la solicitud HTTP.

Los componentes principales son:

- Django: gestiona la lógica de aplicación y las operaciones de la API.
- PostgreSQL: almacena eventos, reportes y alertas.
- Redis: proporciona infraestructura para el broker de tareas y el caching.
- Celery Worker: ejecuta las tareas asíncronas.
- Celery Beat: programa tareas periódicas.

Para una explicación más detallada de los componentes y sus interacciones, consultar [`docs/architecture.md`](docs/architecture.md).

## Requisitos

- Docker
- Docker Compose

## Configuración

Clonar el repositorio:

```bash
git clone https://github.com/Lulipro42/ecommerce-analytics.git
cd ecommerce-analytics
```

Crear el archivo de entorno a partir del ejemplo:

```bash
cp .env.example .env
```

Revisar las variables de entorno y configurarlas según el entorno local.

## Ejecución

Levantar los servicios:

```bash
docker compose up --build
```

Esto inicia los servicios definidos en Docker Compose, incluyendo la aplicación Django, PostgreSQL, Redis, Celery Worker y Celery Beat.

## Pruebas

Ejecutar las pruebas automatizadas desde el entorno de la aplicación:

```bash
docker compose exec web pytest
```

Consultar la configuración de pruebas y los archivos de test para conocer la cobertura disponible.

## Estructura del proyecto

```text
ecommerce-analytics/
├── .github/
│   └── workflows/
├── docs/
│   └── architecture.md
├── src/
│   ├── config/
│   ├── core/
│   │   └── tests/
│   └── manage.py
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## Alcance del proyecto

Pulse Analytics es un proyecto de portfolio orientado al desarrollo backend. Su objetivo es demostrar la integración de una API, persistencia relacional, procesamiento asíncrono, caching, generación de reportes y pruebas automatizadas.

No pretende representar una plataforma de analytics empresarial ni un sistema de producción con garantías de disponibilidad o escalabilidad.