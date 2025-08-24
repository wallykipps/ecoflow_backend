from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.core.management import call_command
from smartPlug_devices.ecoflow import smart_plug_data_aggregate
from smartPlug_devices.models import SmartPlug, SmartPlugData

# @shared_task
# def sync_ecoflow_task():
#     call_command('sync_ecoflow')


@shared_task
def sync_ecoflow_task():
    from smartPlug_devices.management.commands.sync_ecoflow import Command
    cmd = Command()
    cmd.sync_smart_plugs()
    cmd.sync_smart_plug_data()

@shared_task
def aggregate_smart_plug_data_all_devices(interval_seconds=300):
    print("⏱️ Starting aggregation for all devices...")
    device_sns = SmartPlug.objects.values_list('sn', flat=True)
    for sn in device_sns:
        try:
            smart_plug_data_aggregate(sn, interval_seconds)
        except Exception as e:
            print(f"❌ Error processing {sn}: {e}")
    print("✅ Aggregation loop complete.")

@shared_task
def delete_old_aggregated_data():
    """
    Delete SmartPlugData records that are older than 12 hours and are marked as is_aggregated=True.
    """
    cutoff_time = timezone.now() - timedelta(hours=2)
    deleted_count, _ = SmartPlugData.objects.filter(
        is_aggregated=True,
        eatTime__lt=cutoff_time
    ).delete()
    print(f"🧹❌Deleted {deleted_count} old aggregated SmartPlugData records.")

@shared_task
def push_aggregated_data_to_prospect():
    from smartPlug_devices.ecoflow import push_smart_plug_data_to_prospect
    result = push_smart_plug_data_to_prospect()
    
    if result.get("success"):
        print(f"✅ Successfully pushed data")
    else:
        print(f"❌ Push failed: {result.get('error')}")