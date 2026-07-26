import os
from celery import Celery
from celery.schedules import crontab


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('pulse_analytics')  # ← esto es lo que busca Celery

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

app.conf.beat_schedule = {
    'verificar-alertas-ventas-cada-5-min': {
        'task': 'core.tasks.verificar_alertas_ventas',
        'schedule': 300.0,  # 5 minutos
    },
}