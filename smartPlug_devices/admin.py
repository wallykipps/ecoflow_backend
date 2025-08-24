from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import SmartPlug, SmartPlugData, SmartPlugDataAggregate

@admin.register(SmartPlug)
class SmartPlugDeviceAdmin(ImportExportModelAdmin):
    list_display = ('name', 'sn', 'online','productName', 'last_updated')
    search_fields = ('name', 'sn', 'model')
    readonly_fields = ('last_updated',)
    ordering = ('name',)

@admin.register(SmartPlugData)
class DeviceQuotaAdmin(ImportExportModelAdmin):
    list_display = (
        'device','id','serial_number',  'eatTime', 'country', 'town', 'switchStatus', 'volt','current_calculated', 'current', 'watts', 
        'freq','updateTime','fetched_at','utcTime','timeZone','is_aggregated',
    )
    search_fields = ('device__name', 'device__sn')
    readonly_fields = ('fetched_at',)
    ordering = ('-fetched_at',)
    list_filter = ('fetched_at',)

@admin.action(description='❌ Delete ALL SmartPlugData records')
def delete_all_smartplug_data(modeladmin, request, queryset):
    SmartPlugData.objects.all().delete()


@admin.register(SmartPlugDataAggregate)
class DeviceQuotaAdmin(ImportExportModelAdmin):
    list_display = (
        'device',  'manufacturer', 'serial_number', 'country', 'town', 'switchStatus', 'metered_at', 'interval_seconds', 'phase', 'voltage_v', 'current_a', 
        'frequency_hz','power_w','power_factor','energy_interval_wh','energy_lifetime_wh','billing_cycle_start_at','is_pushed'
    )
    search_fields = ('device__name', 'device__sn')
    readonly_fields = ('metered_at',)
    ordering = ('-metered_at',)
    list_filter = ('metered_at',)


