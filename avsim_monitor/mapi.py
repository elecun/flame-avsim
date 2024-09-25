
'''
Message API definitions
@author Byunghun Hwang(bh.hwang@iae.re.kr)
'''

import json

class mapi():
    
    def __init__(self):
        self.decl_mapi = {
            #for manager
            "flame/avsim/mapi_notify_active" : self.mapi_notify_active,
        }
    
    # active notification
    def mapi_notify_active(self, app:str, active:bool) -> str:
        msg = {"app":app, "active":active}
        return json.dumps(msg)