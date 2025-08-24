from django.core.management.base import BaseCommand
from smartPlug_devices.models import SmartPlug, SmartPlugData
from smartPlug_devices.ecoflow import get_device_list, get_ecoflow_devices_all
from datetime import datetime, timezone, timedelta

def extract_selected_quota_fields(quota: dict) -> dict:
    return {
        'utcTime': quota.get("2_1.utcTime"),
        'updateTime': quota.get("2_1.updateTime"),
        'timeZone': quota.get("2_1.timeZone"),
        'country': quota.get("2_1.country"),
        'town': quota.get("2_1.town"),
        'switchStatus': quota.get("2_1.switchSta"),
        'freq': quota.get("2_1.freq"),
        'volt': quota.get("2_1.volt"),
        'current': quota.get("2_1.current"),
        'watts': quota.get("2_1.watts"),
    }

class Command(BaseCommand):
    help = "Sync EcoFlow smart plugs and their quota data into the database"

    def handle(self, *args, **options):
        self.stdout.write("Starting sync of SmartPlugs...")
        self.sync_smart_plugs()
        self.stdout.write("SmartPlugs synced successfully.")

        self.stdout.write("Starting sync of SmartPlugData...")
        self.sync_smart_plug_data()
        self.stdout.write("SmartPlugData synced successfully.")

   
    # def sync_smart_plugs(self):
    #     device_list = get_device_list()

    #     for device in device_list:
    #         SmartPlug.objects.update_or_create(
    #             sn=device["sn"],
    #             defaults={
    #                 "name": device["name"],
    #                 "model": device["model"],
    #                 "status": device["status"],
    #                 "full_info": device["full_info"],
    #             }
    #         )

    def sync_smart_plugs(self):
        device_list = get_device_list()

        for device in device_list:
            full_info = device.get("full_info", {})

            SmartPlug.objects.update_or_create(
                sn=device["sn"],
                defaults={
                    "name": device["name"],
                    "model": device["model"],
                    "status": device["status"],
                    "online": full_info.get("online"),
                    "productName": full_info.get("productName"),
                    "full_info": full_info,
                }
            )

    
    
    def sync_smart_plug_data(self):
        devices = get_ecoflow_devices_all()
        smart_plug_map = {plug.sn: plug for plug in SmartPlug.objects.all()}

        for device_data in devices:
            sn = device_data["sn"]
            plug = smart_plug_map.get(sn)
            if not plug:
                self.stdout.write(f"Warning: SmartPlug with SN {sn} not found, skipping quota data.")
                continue

            quota = device_data.get("quota", {})
            extracted = extract_selected_quota_fields(quota)
    # Convert utcTime to EAT datetime string
            raw_utc_time = extracted.get("utcTime")

            if raw_utc_time:
                try:
                    # Parse raw UTC timestamp
                    utc_dt = datetime.fromtimestamp(int(raw_utc_time), tz=timezone.utc)
                    eat_dt = utc_dt.astimezone(timezone(timedelta(hours=3)))

                    formatted_utc_time = utc_dt.strftime("%Y-%m-%d %H:%M:%S")
                    formatted_eat_time = eat_dt.strftime("%Y-%m-%d %H:%M:%S")

                except Exception as e:
                    self.stdout.write(f"Error parsing utcTime for {sn}: {e}")
                    formatted_utc_time = None
                    formatted_eat_time = None
            else:
                formatted_utc_time = None
                formatted_eat_time = None



            SmartPlugData.objects.create(
                device=plug,
                utcTime=formatted_utc_time,
                eatTime=formatted_eat_time,
                updateTime=extracted["updateTime"],
                timeZone=extracted["timeZone"],
                country=extracted["country"],
                town=extracted["town"],
                switchStatus=extracted["switchStatus"],
                freq=extracted["freq"],
                volt=extracted["volt"],
                current=extracted["current"],
                watts=(extracted["watts"] / 10) if extracted["watts"] is not None else None,
                quota_data=quota,
            )
