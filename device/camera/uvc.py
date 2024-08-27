'''
General USB Interface Camera Controller Class
@author Byunghun Hwang <bh.hwang@iae.re.kr>
'''

from PyQt6.QtCore import QObject, Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QImage
import cv2
from datetime import datetime
from util.logger.video import VideoRecorder
import platform
from util.logger.console import ConsoleLogger
from vision.camera.interface import ICamera
import numpy as np


# camera device class
class UVC(ICamera):
    def __init__(self, camera_id: int) -> None:
        super().__init__(camera_id)
        
        self.camera_id = camera_id  # camera ID
        self.__grabber = None         # device instance
        self.__console = ConsoleLogger.get_logger()
    
    # open camera device    
    def open(self) -> bool:
        try:
            os_system = platform.system()
            if os_system == "Darwin": #MacOS
                self.__grabber = cv2.VideoCapture(self.camera_id)
            elif os_system == "Linux": # Linux
                self.__grabber = cv2.VideoCapture(self.camera_id, cv2.CAP_V4L2) # video capture instance with opencv
            elif os_system == "Windows":
                self.__grabber = cv2.VideoCapture(self.camera_id)
            else:
                raise Exception("Unsupported Camera")

            if not self.__grabber.isOpened():
                return False

        except Exception as e:
            self.__console.critical(f"{e}")
            return False
        return True
    
    # close camera device
    def close(self) -> None:
        if self.__grabber:
            self.__grabber.release()
    
    # captrue image
    def grab(self):
        return self.__grabber.read() # grab
    
    # check device open
    def is_opened(self) -> bool:
        return self.__grabber.isOpened()
    
    # get camera properties
    def get_properties(self):
        fps = self.__grabber.get(cv2.CAP_PROP_FPS)
        w = int(self.__grabber.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self.__grabber.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return (fps, w, h)

# camera controller class
class Controller(QThread):

    frame_update_signal = pyqtSignal(np.ndarray, float) # to gui and process

    def __init__(self, camera_id:int):
        super().__init__()
        
        self.__console = ConsoleLogger.get_logger()   # console logger
        self.__uvc_camera = UVC(camera_id)    # UVC camera device
    
    # get camera id from own camera device    
    def get_camera_id(self) -> int:
        return self.__uvc_camera.camera_id

    # camera device open
    def open(self) -> bool:
        try:
            return self.__uvc_camera.open()

        except Exception as e:
            self.__console.critical(f"{e}")
        
        return False

    # camera pixel resolution
    def get_pixel_resolution(self) -> (int, int):
        fps, w, h = self.__uvc_camera.get_properties()
        return (w,h)
    
    # camera device close
    def close(self) -> None:
        self.requestInterruption() # to quit for thread
        self.quit()
        self.wait(1000)

        # release grabber
        self.__uvc_camera.close()
        self.__console.info(f"camera {self.__uvc_camera.camera_id} controller is closed")

    # start thread
    def begin(self):
        if self.__uvc_camera.is_opened():
            self.start()
        else:
            self.__console.warning("Camera is not ready")
    
    # return camera id
    def __str__(self):
        return str(self.__uvc_camera.camera_id)
    
    def grab(self):
        return self.__uvc_camera.grab()
    
    # image grab with thread
    def run(self):
        while True:
            if self.isInterruptionRequested():
                break
            
            t_start = datetime.now()
            ret, frame = self.__uvc_camera.grab()

            if ret:                
                t_end = datetime.now()
                framerate = float(1./(t_end - t_start).total_seconds())

                self.frame_update_signal.emit(frame, framerate)
    
