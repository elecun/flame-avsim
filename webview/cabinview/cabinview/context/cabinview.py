
from django.conf import settings

'''
User global variable definitions
'''
def context_processors(request):
    return {
        'system':{ 
            'title':'FLAME-AV-Simulator',
            'company':"IAE",
            'version':"0.1.0",
            'host':'localhost:8000',
            'mqtt_broker_ip':str(settings.MQTT_BROKER_ADDRESS),
            'mqtt_broker_port':int(settings.MQTT_BROKER_WEBSCOKET)
            },
        'frontend':{

        },
        'backend':{

        }
    }


