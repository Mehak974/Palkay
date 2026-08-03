import os
from celery import Celery
from decouple import config

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'palkay.settings')

app = Celery('palkay')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery broker configuration
app.conf.broker_url = config('REDIS_URL', default='redis://127.0.0.1:6379/0')
app.conf.result_backend = config('REDIS_URL', default='redis://127.0.0.1:6379/0')

# Periodic tasks schedules
from celery.schedules import crontab

app.conf.beat_schedule = {
    'cancel-pending-orders-every-15-mins': {
        'task': 'orders.tasks.auto_cancel_pending_orders',
        'schedule': crontab(minute='*/15'),
    },
    'cleanup-expired-carts-daily': {
        'task': 'cart.tasks.cleanup_expired_carts',
        'schedule': crontab(hour=2, minute=0),
    },
}
app.conf.timezone = 'America/Chicago'
