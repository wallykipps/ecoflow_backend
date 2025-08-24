import time
import hmac
import hashlib
import requests
from django.conf import settings
import secrets
from datetime import datetime, timezone, timedelta
import pandas as pd
from django.utils.timezone import now
from django.utils.timezone import make_aware, is_naive
from datetime import datetime, timezone, timedelta
import pytz
from smartPlug_devices.models import SmartPlug, SmartPlugData, SmartPlugDataAggregate 


# --- EcoFlow API Credentials ---
ACCESS_KEY = settings.ECOFLOW_ACCESS_KEY
SECRET_KEY = settings.ECOFLOW_SECRET_KEY
BASE_URL = settings.ECOFLOW_BASE_URL


def generate_signature(params: dict, timestamp: int, nonce: str) -> str:
    sorted_params = sorted(params.items(), key=lambda x: x[0])
    if sorted_params:
        param_str = '&'.join(f"{k}={v}" for k, v in sorted_params)
        param_str += f"&accessKey={ACCESS_KEY}&nonce={nonce}&timestamp={timestamp}"
    else:
        param_str = f"accessKey={ACCESS_KEY}&nonce={nonce}&timestamp={timestamp}"

    sign = hmac.new(
        SECRET_KEY.encode('utf-8'),
        param_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return sign


def get_all_devices():
    path = "/iot-open/sign/device/list"
    timestamp = int(time.time() * 1000)
    nonce = str(secrets.randbelow(1000000)).zfill(6)
    sign = generate_signature({}, timestamp, nonce)

    url = BASE_URL + path
    headers = {
        "accessKey": ACCESS_KEY,
        "timestamp": str(timestamp),
        "nonce": nonce,
        "sign": sign,
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    data = response.json()
    if data.get("code") != "0":
        raise Exception(f"API Error: {data.get('message')} (Code: {data.get('code')})")
    return data.get("data", [])

def get_device_list():
    devices = get_all_devices()
    results = []

    if not devices:
        return []

    for device in devices:
        results.append({
            "name": device.get("deviceName") or "Unnamed Device",
            "sn": device.get("sn"),
            "model": device.get("model", "Unknown"),
            "status": device.get("status", "Unknown"),
            "full_info": device,
        })

    return results


def get_ecoflow_devices_all():
    devices = get_all_devices()
    results = []

    if not devices:
        return []

    for device in devices:
        sn = device.get("sn")
        device_data = {
            "name": device.get("deviceName") or "Unnamed Device",
            "sn": sn,
            "model": device.get("model", "Unknown"),
            "status": device.get("status", "Unknown"),
            "full_info": device,
            "quota": {},
            "quota_error": None
        }

        if sn:
            try:
                path = "/iot-open/sign/device/quota/all"
                query_params = {"sn": sn}
                timestamp = int(time.time() * 1000)
                nonce = str(secrets.randbelow(1000000)).zfill(6)
                sign = generate_signature(query_params, timestamp, nonce)
                url = f"{BASE_URL}{path}?sn={sn}"
                headers = {
                    "accessKey": ACCESS_KEY,
                    "timestamp": str(timestamp),
                    "nonce": nonce,
                    "sign": sign,
                }

                response = requests.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()

                if data.get("code") == "0":
                    device_data["quota"] = data.get("data", {})
                else:
                    device_data["quota_error"] = f"API Error: {data.get('message')} (Code: {data.get('code')})"

            except Exception as e:
                device_data["quota_error"] = str(e)

        results.append(device_data)

    return results

def extract_selected_full_info_fields(full_info: dict) -> dict:
    return {
        'online': full_info.get("online"),
        'productName': full_info.get("productName"),

    }

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


# def sync_smart_plugs():
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


def sync_smart_plugs():
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



def sync_smart_plug_data():
    devices = get_ecoflow_devices_all()

    for device_data in devices:
        sn = device_data["sn"]
        try:
            # plug = SmartPlug.objects.get(sn=sn)
            # sn_value = plug.sn if plug and plug.sn else "MISSING"
            plug = SmartPlug.objects.get(sn=sn)
            plug.refresh_from_db()  # Ensures the latest data is loaded
            sn_value = plug.sn if plug.sn else "MISSING"
            #print("Creating SmartPlugData with serial_number =", sn_value)
            quota = device_data.get("quota", {})
            extracted = extract_selected_quota_fields(quota)

            raw_utc_time = extracted.get("utcTime")

            if raw_utc_time:
                try:
                    # Parse raw UTC timestamp
                    # Parse UTC timestamp directly to an aware datetime
                    utc_dt = datetime.fromtimestamp(int(raw_utc_time), tz=timezone.utc)

                    # Convert to EAT (UTC+3)
                    eat_tz = timezone(timedelta(hours=3))
                    eat_dt = utc_dt.astimezone(eat_tz)

                            # Ensure timezone-awareness
                    if is_naive(eat_dt):
                        eat_dt = make_aware(eat_dt, timezone=eat_tz)
                    

                    # formatted_utc_time = utc_dt.strftime("%Y-%m-%d %H:%M:%S")
                    # formatted_eat_time = eat_dt.strftime("%Y-%m-%d %H:%M:%S")

                except Exception as e:
                    eat_dt = None
                    # formatted_utc_time = None
                    # formatted_eat_time = None
            else:
                eat_dt = None
                # formatted_utc_time = None
                # formatted_eat_time = None

            SmartPlugData.objects.create(
                device=plug,
                serial_number=sn_value,
                utcTime=extracted['utcTime'],
                #eatTime=formatted_eat_time,
                eatTime=eat_dt,
                updateTime=extracted['updateTime'],
                timeZone=extracted['timeZone'],
                country=extracted['country'],
                town=extracted['town'],
                switchStatus=extracted['switchStatus'],
                freq=extracted['freq'],
                volt=extracted['volt'],
                current=extracted['current'],
                watts=(extracted["watts"] / 10) if extracted["watts"] is not None else None,
                quota_data=quota,
            )
        except SmartPlug.DoesNotExist:
            # Optional: log or handle missing device
            print(f"SmartPlug with SN {sn} not found; skipping quota data.")

def smart_plug_data_aggregate(device_sn, interval_seconds=300):
    print(f">>> Running aggregation for {device_sn}")
    from django.utils.timezone import utc

    try:
        device = SmartPlug.objects.get(sn=device_sn)
    except SmartPlug.DoesNotExist:
        print(f"Device with SN {device_sn} not found.")
        return

    # Load only unaggregated records
    qs = SmartPlugData.objects.filter(device=device, is_aggregated=False).order_by('eatTime')
    if not qs.exists():
        print(f"No unaggregated SmartPlugData for device {device_sn}")
        return

    # Load into DataFrame
    df = pd.DataFrame(list(qs.values(
        'id', 'eatTime', 'volt', 'current', 'freq', 'watts',
        'switchStatus', 'country', 'town'
    )))

    df.rename(columns={
        'eatTime': 'timestamp',
        'volt': 'voltage_v',
        'current': 'current_a',
        'freq': 'frequency_hz',
        'watts': 'power_w',
    }, inplace=True)

    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    df.set_index('timestamp', inplace=True)

    # Map record IDs to resample bins
    df['resample_bin'] = df.index.floor(f'{interval_seconds}s')
    id_map = df.groupby('resample_bin')['id'].apply(list).to_dict()

    print(f"[DEBUG] Sample bin ID map: {dict(list(id_map.items())[:2])}")

    # Resample and aggregate
    agg = df.resample(f"{interval_seconds}s").agg({
        'voltage_v': 'mean',
        'current_a': 'mean',
        'frequency_hz': 'mean',
        'power_w': 'mean',
        'switchStatus': 'last',
        'country': 'last',
        'town': 'last',
    }).dropna(subset=['power_w'])

    if agg.empty:
        print(f"No data to aggregate for {device_sn}")
        return

    # Energy calculation
    interval_hours = interval_seconds / 3600
    agg['energy_interval_wh'] = agg['power_w'] * interval_hours
    # Get last cumulative energy value for the device
    last_agg = SmartPlugDataAggregate.objects.filter(device=device).order_by('-metered_at').first()
    last_lifetime_wh = last_agg.energy_lifetime_wh if last_agg else 0.0

    # Add it to the new cumulative energy values
    agg['energy_lifetime_wh'] = agg['energy_interval_wh'].cumsum() + last_lifetime_wh

    for timestamp, row in agg.iterrows():
        SmartPlugDataAggregate.objects.update_or_create(
            device=device,
            metered_at=timestamp,
            interval_seconds=interval_seconds,
            defaults={
                'serial_number': device.sn,
                'manufacturer': 'Ecoflow',
                'country': row.get('country'),
                'town': row.get('town'),
                'switchStatus': row.get('switchStatus'),
                'phase': '1',
                'voltage_v': round(row.get('voltage_v', 0), 2),
                'current_a': round(row.get('current_a', 0), 2),
                'frequency_hz': round(row.get('frequency_hz', 0), 2),
                'power_w': round(row.get('power_w', 0), 2),
                'power_factor': 1.0,
                'energy_interval_wh': round(row.get('energy_interval_wh', 0), 2),
                'energy_lifetime_wh': round(row.get('energy_lifetime_wh', 0), 2),
                'billing_cycle_start_at': None,
            }
        )

    # ✅ Mark ALL fetched records as aggregated
    all_ids = list(qs.values_list('id', flat=True))
    print(f">>> Updating {len(all_ids)} records to is_aggregated=True")
    SmartPlugData.objects.filter(id__in=all_ids).update(is_aggregated=True)
    print(">>> Aggregation flag updated for all fetched records.")

    print(f"✅ Aggregation complete for {device_sn}. {len(agg)} intervals processed.")


def push_smart_plug_data_to_prospect():
    unpushed_records = SmartPlugDataAggregate.objects.filter(is_pushed=False).order_by("metered_at")

    if not unpushed_records.exists():
        return {"message": "No unpushed records found."}

    # Build the payload
    payload = {
        "data": [
            {
                "manufacturer": agg.manufacturer,
                "serial_number": agg.serial_number,
                "metered_at": agg.metered_at.strftime("%Y-%m-%d %H:%M:%S"),
                "phase": agg.phase,
                "voltage_v": agg.voltage_v,
                "power_factor": agg.power_factor,
                "power_w": agg.power_w,
                "energy_lifetime_wh": agg.energy_lifetime_wh,
                "energy_interval_wh": agg.energy_interval_wh,
                "frequency_hz": agg.frequency_hz,
                "current_a": agg.current_a,
                "interval_seconds": agg.interval_seconds,
                "billing_cycle_start_at": agg.billing_cycle_start_at.strftime("%Y-%m-%d") if agg.billing_cycle_start_at else None,
            }
            for agg in unpushed_records
        ]
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.PROSPECT_API_TOKEN}",
    }

    try:
        response = requests.post(settings.PROSPECT_API_URL, json=payload, headers=headers)
        response.raise_for_status()

        # If successful, update all records at once
        unpushed_records.update(is_pushed=True)

        return {
            "success": True,
            "pushed_count": unpushed_records.count(),
        }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": str(e),
        }

