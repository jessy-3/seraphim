"""
Celery configuration for Seraphim project
"""
import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seraphim.settings')

app = Celery('seraphim')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat schedule for periodic tasks
app.conf.beat_schedule = {
    # Fetch OHLC data every hour
    'fetch-ohlc-data-hourly': {
        'task': 'api.tasks.fetch_ohlc_data',
        'schedule': crontab(minute='5'),  # Every hour at 5 minutes past
    },
    # Calculate indicators every hour (after OHLC fetch)
    'calculate-indicators-hourly': {
        'task': 'api.tasks.calculate_indicators',
        'schedule': crontab(minute='10'),  # Every hour at 10 minutes past
    },
    # Calculate EMA channel every hour
    'calculate-ema-channel-hourly': {
        'task': 'api.tasks.calculate_ema_channel',
        'schedule': crontab(minute='15'),  # Every hour at 15 minutes past
    },
    # Calculate market regime every hour
    'calculate-market-regime-hourly': {
        'task': 'api.tasks.calculate_market_regime',
        'schedule': crontab(minute='20'),  # Every hour at 20 minutes past
    },
    # Generate trading signals every hour
    'generate-trading-signals-hourly': {
        'task': 'api.tasks.generate_trading_signals',
        'schedule': crontab(minute='25'),  # Every hour at 25 minutes past
    },
}

app.conf.timezone = 'UTC'

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

