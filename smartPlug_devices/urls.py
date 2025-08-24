from django.urls import path
from .views import get_devices, device_list

urlpatterns = [
    path('api/device_list', device_list),
    path('api/devices_data', get_devices),
]
