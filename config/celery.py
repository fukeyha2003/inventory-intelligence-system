"""
Celery Configuration for Fashion Inventory System
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Create Celery app
app = Celery('fashion_inventory_system')

# Load config from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# Periodic task schedule
app.conf.beat_schedule = {
    # Generate forecasts daily at 2 AM
    'generate-daily-forecasts': {
        'task': 'ml_engine.tasks.generate_daily_forecasts',
        'schedule': crontab(hour=2, minute=0),
    },
    
    # Retrain models weekly on Sunday at 3 AM
    'retrain-models-weekly': {
        'task': 'ml_engine.tasks.train_models_task',
        'schedule': crontab(hour=3, minute=0, day_of_week='sunday'),
    },
    
    # Update risk analysis daily at 4 AM
    'update-risk-analysis': {
        'task': 'ml_engine.tasks.update_risk_analysis_task',
        'schedule': crontab(hour=4, minute=0),
    },
    
    # Detect trends daily at 5 AM
    'detect-trends': {
        'task': 'ml_engine.tasks.detect_trends_task',
        'schedule': crontab(hour=5, minute=0),
    },
    
    # Send alerts daily at 8 AM
    'send-daily-alerts': {
        'task': 'ml_engine.tasks.send_alert_emails_task',
        'schedule': crontab(hour=8, minute=0),
    },
}

# Celery configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max per task
)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to test Celery setup"""
    print(f'Request: {self.request!r}')