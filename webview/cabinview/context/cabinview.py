
from django.conf import settings

'''
User global variable definitions
'''
def context_processors(request):
    return {
        'system':{ 
            'title':'Flame AVSIM Cabinview',
            'company':"IAE",
            'version':"0.1.0",
            'host':"127.0.0.1",
            'port':"8000",
            'mqtt_broker_ip':"192.168.0.12",
            'mqtt_broker_wsport':8083
            },
        'frontend':{

        },
        'backend':{

        }
    }