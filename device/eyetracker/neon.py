'''
NEON Eyetracker Control module
@author Byunghun Hwang<bh.hwang@iae.re.kr>
'''

from pupil_labs.realtime_api.simple import discover_one_device
from pupil_labs.realtime_api import device
from util.logger.console import ConsoleLogger
import asyncio
import time
import paho.mqtt.client as mqtt
import json

try:
    from PyQt5.QtCore import QObject, Qt, QTimer, QThread, pyqtSignal
    from PyQt5.QtGui import QImage
except ImportError:
    from PyQt6.QtCore import QObject, Qt, QTimer, QThread, pyqtSignal
    from PyQt6.QtGui import QImage

class neon_controller(QObject):
    status_update_signal = pyqtSignal(dict)

    def __init__(self, config):
        super().__init__()
        self.__console = ConsoleLogger.get_logger()

    def __delattr__(self, __name: str) -> None:
        print("closing..")
        #self.close() # device close

    # device discover
    def device_discover(self):
        self.__console.info("Discover eyetracker device...")
        self.device = discover_one_device(max_search_duration_seconds=5)
        self.status_update_signal.emit(self.device_info())
    
    # device close
    def close(self):
        try:
            if self.device:
                self.device.close()
                self.__console.info("Eyetracker device is closed")
        except RuntimeError as e:
            print(f"Runtime Error : {e}")

        # recording start
    def record_start(self):
        if self.device:
            try:
                record_id = self.device.recording_start()
                print("start recording")
                print(record_id)
            except device.DeviceError as e:
                print(f"Device Error : {e}")

    # recording stop
    def record_stop(self):
        if self.device:
            try:
                ret = self.device.recording_stop_and_save()
                print("stop recording")
                print(ret)
            except device.DeviceError as e:
                print(f"Device Error : {e}")

    # get device info
    def device_info(self) -> dict:
        info = {}
        if self.device:
            info["address"] = self.device.address
            info["name"] = self.device.phone_name
            info["battery_level"] = self.device.battery_level_percent
            info["battery_state"] = self.device.battery_state
            info["free_storage"] = self.device.memory_num_free_bytes/1024**3
            info["memory_state"] = self.device.memory_state
        return info
    







class neon_controller2(QThread):

    status_update_signal = pyqtSignal(dict)

    def __init__(self, config):
        super().__init__()
        self.__console = ConsoleLogger.get_logger()

        self.device = asyncio.run(self.device_discover())
        self.__is_running = True
        self.__interval = 10 # update info interval

        # message api definitions
        self.message_api = {
            "flame/avsim/neon/mapi_record_start" : self.mapi_record_start,
            "flame/avsim/neon/mapi_record_stop" : self.mapi_record_stop
        }

        # MQTT-based message api pipeline
        self.mq_client = mqtt.Client(client_id="neon_controller", transport='tcp', protocol=mqtt.MQTTv311, clean_session=True)
        self.mq_client.on_connect = self.on_mqtt_connect
        self.mq_client.on_message = self.on_mqtt_message
        self.mq_client.on_disconnect = self.on_mqtt_disconnect
        self.mq_client.connect_async(config["broker_ip"], port=1883, keepalive=60)
        self.mq_client.loop_start()

    # thread loop function
    def run(self):
        while True:
            if not self.__is_running:
                self.close()
                self.__console.info("Eyetracker device is closed")
                break
            self.status_update_signal.emit(self.device_info())
            self.sleep(self.__interval) # 5sec

    # set thread stop flag
    def stop(self):
        self.__is_running = False

    def is_working(self) -> bool:
        if self.device and self.__is_running:
            return True
        return False


    # device discover
    async def device_discover(self):
        return discover_one_device(max_search_duration_seconds=5)
    
    # get device info
    def device_info(self) -> dict:
        info = {}
        if self.device:
            info["address"] = self.device.address
            info["name"] = self.device.phone_name
            info["battery_level"] = self.device.battery_level_percent
            info["battery_state"] = self.device.battery_state
            info["free_storage"] = self.device.memory_num_free_bytes/1024**3
            info["memory_state"] = self.device.memory_state
        
        return info
    
    # device close
    def close(self):
        try:
            if self.device:
                self.device.close()
        except RuntimeError as e:
            self.__console.critical(f"Eyetracker Exception : {e}")

    # message api for record start
    def mapi_record_start(self, payload):
        self.record_start()
    
    # message api for record stop
    def mapi_record_stop(self, payload):
        self.record_stop()  
    
    # recording start
    def record_start(self):
        if self.device:
            try:
                record_id = self.device.recording_start()
                self.__console.info(f"Eyetracker Record ID : {record_id}")
            except device.DeviceError as e:
                self.__console.critical(f"Eyetracker Exception : {e}")

    # recording stop
    def record_stop(self):
        if self.device:
            try:
                ret = self.device.recording_stop_and_save()
            except device.DeviceError as e:
                self.__console.critical(f"Eyetracker Exception : {e}")

    # mqtt connection
    def on_mqtt_connect(self, mqttc, obj, flags, rc):
        # subscribe message api
        for topic in self.message_api.keys():
            self.mq_client.subscribe(topic, 0)
        
        self.__console(f"[Eyetracker] Ready to MAPI ({rc})")
        
    def on_mqtt_disconnect(self, mqttc, userdata, rc):
        self.__console(f"[Eyetracker] MAPI is not available")

    # message parser with MQTT
    def on_mqtt_message(self, mqttc, userdata, msg):
        mapi = str(msg.topic)
        
        try:
            if mapi in self.message_api.keys():
                payload = json.loads(msg.payload)
                if "app" not in payload:
                    self.__console.info(f"[Eyetracker] Message payload does not contain the app")
                    return
                
                if payload["app"] != "avsim_monitor":
                    self.message_api[mapi](payload)
            else:
                self.__console.info(f"[Eyetracker] Unknown MAPI {mapi}")

        except json.JSONDecodeError as e:
            print("MAPI Message payload cannot be converted")
