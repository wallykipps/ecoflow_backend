from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from smartPlug_devices.ecoflow import get_ecoflow_devices_all, get_device_list, sync_smart_plug_data, sync_smart_plugs

@api_view(['GET'])
def device_list(request):
    try:
        data = get_device_list()
        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['GET'])
def get_devices(request):
    try:
        data = get_ecoflow_devices_all()
        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    


