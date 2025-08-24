from django.db import models
from decimal import Decimal, ROUND_HALF_UP

class SmartPlug(models.Model):
    sn = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255, default="Unnamed Device")
    model = models.CharField(max_length=100, default="Unknown")
    status = models.CharField(max_length=50, default="Unknown")
    online = models.BooleanField(null=True, blank=True)
    productName = models.CharField(max_length=200, null=True, blank=True)
    full_info = models.JSONField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.sn})"


class SmartPlugData(models.Model):
    device = models.ForeignKey(SmartPlug, on_delete=models.CASCADE, related_name='quotas')
    serial_number = models.CharField(max_length=100, null=False, blank=False)
    utcTime = models.CharField(max_length=100, null=True, blank=True)     # Store UTC time
    #eatTime = models.CharField(max_length=100, null=True, blank=True)     # Store EAT time
    # models.py
    eatTime = models.DateTimeField(null=True, blank=True)
    updateTime = models.CharField(max_length=100, null=True, blank=True)
    timeZone = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    town = models.CharField(max_length=100, null=True, blank=True)
    switchStatus = models.IntegerField(null=True, blank=True)
    freq = models.FloatField(null=True, blank=True)
    volt = models.FloatField(null=True, blank=True)
    current= models.FloatField(null=True, blank=True) 
    current_calculated= models.FloatField(null=True, blank=True) #raw current
    watts = models.FloatField(null=True, blank=True)
    quota_data = models.JSONField()
    fetched_at = models.DateTimeField(auto_now_add=True)
    is_aggregated = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.device:
            raise ValueError("Device must be set to inherit serial_number.")
        if not self.serial_number:
            self.serial_number = self.device.sn
        super().save(*args, **kwargs)

       
    @property
    def current_calculated(self):
        try:
            if self.watts is not None and self.volt:
                value = Decimal(self.watts) / Decimal(self.volt)
                return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except (ZeroDivisionError, TypeError):
            return None

    
    def __str__(self):
        return f"Quota data for {self.device} at {self.fetched_at}"
    

class SmartPlugDataAggregate(models.Model):
    device = models.ForeignKey(SmartPlug, on_delete=models.CASCADE, related_name='aggregates')
    manufacturer = models.CharField(max_length=100, default='Ecoflow')
    serial_number = models.CharField(max_length=100)
    country = models.CharField(max_length=100, null=True, blank=True)
    town = models.CharField(max_length=100, null=True, blank=True)
    switchStatus = models.IntegerField(null=True, blank=True)
    metered_at = models.DateTimeField()  # end of the aggregation interval
    interval_seconds = models.IntegerField(default=600)  # default 10-minute interval
    phase = models.CharField(max_length=10, default='1')
    voltage_v = models.FloatField(null=True, blank=True)
    current_a = models.FloatField(null=True, blank=True)
    frequency_hz = models.FloatField(null=True, blank=True)
    power_w = models.FloatField(null=True, blank=True)
    power_factor = models.FloatField(null=True, blank=True, default=1.0)
    energy_interval_wh = models.FloatField(null=True, blank=True)
    energy_lifetime_wh = models.FloatField(null=True, blank=True)
    billing_cycle_start_at = models.DateTimeField(null=True, blank=True)
    is_pushed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.device:
            raise ValueError("Device must be set to inherit serial_number.")
        if not self.serial_number:
            self.serial_number = self.device.sn
        super().save(*args, **kwargs)
    
    
    def __str__(self):
        return f"Aggregated data for {self.device} at {self.metered_at}"

