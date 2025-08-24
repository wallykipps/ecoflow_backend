import os
from celery import Celery
from celery.schedules import schedule

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartPlug_api.settings')

app = Celery('smartPlug_api')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Add beat schedule here:
app.conf.beat_schedule = {
    'sync-ecoflow-every-10-seconds': {
        'task': 'smartPlug_devices.tasks.sync_ecoflow_task',
        'schedule': 10.0,
    },

    'aggregate-data-every-minute': {
        'task': 'smartPlug_devices.tasks.aggregate_smart_plug_data_all_devices',
        'schedule': 300.0,  # every 5 minutes
    },
    'delete-old-aggregated-data-every-hour': {
        'task': 'smartPlug_devices.tasks.delete_old_aggregated_data',
        'schedule': 3600.0,  # every 1 hour
    },
    'push-data-to-prospect': {
        'task': 'smartPlug_devices.tasks.push_aggregated_data_to_prospect',
        'schedule': 3600,   # every 1 hour
    },
}