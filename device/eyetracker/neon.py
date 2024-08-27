'''
NEON Eyetracker Control module
@author Byunghun Hwang<bh.hwang@iae.re.kr>
'''

from pupil_labs.realtime_api.simple import discover_one_device
from pupil_labs.realtime_api import device
from util.logger.console import ConsoleLogger
import asyncio
import time

try:
    from PyQt5.QtCore import QObject, Qt, QTimer, QThread, pyqtSignal
    from PyQt5.QtGui import QImage
except ImportError:
    from PyQt6.QtCore import QObject, Qt, QTimer, QThread, pyqtSignal
    from PyQt6.QtGui import QImage

class neon_controller(QThread):

    status_update_signal = pyqtSignal(dict)

    def __init__(self, interval):
        super().__init__()
        self.device = asyncio.run(self.device_discover())
        self.__is_running = True
        self.__interval = interval

        self.__console = ConsoleLogger.get_logger()

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
