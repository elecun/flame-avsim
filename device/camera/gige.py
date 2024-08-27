'''
Gigabit Ethernet interface camera device class
@Author <bh.hwang@iae.re.kr>
'''

try:
    from PyQt5.QtCore import QObject, Qt, QTimer, QThread, pyqtSignal
    from PyQt5.QtGui import QImage
except ImportError:
    from PyQt6.QtCore import QObject, Qt, QTimer, QThread, pyqtSignal
    from PyQt6.QtGui import QImage
    
    
import cv2
from datetime import datetime
from util.logger.video import VideoRecorder
import platform
from util.logger.console import ConsoleLogger
from vision.camera.interface import ICamera
import numpy as np
from pypylon import genicam
from pypylon import pylon

#(Note) acA1300-60gc = 125MHz(PTP disabled), 1 Tick = 8ns
#(Note) a2A1920-51gmPRO = 1GHZ, 1 Tick = 1ns
CAMERA_TICK_TIME = 8 

# global variable for camera array
_camera_array_container:pylon.InstantCameraArray = None

# camera device class
class GigE_Basler(ICamera):
    def __init__(self, camera_id: int) -> None:
        super().__init__(camera_id)
        
        self.camera_id = camera_id  # camera ID
        self.__device:pylon.InstantCamera = None        # single camera device instance
        self.__console = ConsoleLogger.get_logger()
        
        self.__converter = pylon.ImageFormatConverter()
        self.__converter.OutputPixelFormat = pylon.PixelType_BGR8packed
        self.__converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned
        
    # open device
    def open(self) -> bool:
        try:
            global _camera_array_container
            self.__device = _camera_array_container[self.camera_id]
            
            if not self.__device.IsOpen():
                self.__device.Open()
                self.__device.StartGrabbing(pylon.GrabStrategy_LatestImageOnly, pylon.GrabLoop_ProvidedByUser)
                #self.__device.StartGrabbing(pylon.GrabStrategy_OneByOne, pylon.GrabLoop_ProvidedByUser)
                #self.__device.StartGrabbing(pylon.GrabStrategy_UpcomingImage, pylon.GrabLoop_ProvidedByUser)
                #self.__device.StartGrabbing(pylon.GrabStrategy_LatestImages)
            
        except Exception as e:
            self.__console.critical(f"{e}")
            return False
        return True
    
    # close camera
    def close(self) -> None:
        if self.__device!=None:
            self.__device.Close()
            self.__device.DetachDevice()
            
        return super().close()
    
    # captrue image
    def grab(self):
        if self.__device.IsGrabbing():
            _grab_result = self.__device.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
            if _grab_result.GrabSucceeded():
                image = self.__converter.Convert(_grab_result)
                raw_image = image.GetArray()
                _grab_result.Release()
                
                return (True, raw_image)
        return (False, None)
            
    # check device open
    def is_opened(self) -> bool:
        if self.__device:
            return self.__device.IsOpen()
        return False
    
# camera controller class
class Controller(QThread):
    
    frame_update_signal = pyqtSignal(np.ndarray, float) # to gui and process
    
    def __init__(self, camera_id:int):
        super().__init__()
        
        self.__console = ConsoleLogger.get_logger()
        self.__camera = GigE_Basler(camera_id)
        
    # getting camera id
    def get_camera_id(self) -> int:
        return self.__camera.camera_id
    
    # camera open
    def open(self) -> bool:
        try:
            if not self.__camera.is_opened():
                return self.__camera.open()
            else:
                self.__console.warning(f"Camera {self.__camera.get_camera_id()} is already opened")
        except Exception as e:
            self.__console.critical(f"{e}")
        return False
    
    # camera close
    def close(self) -> None:
        self.requestInterruption() # to quit for thread
        self.quit()
        self.wait(1000)

        # release grabber
        self.__camera.close()
        self.__console.info(f"camera {self.__camera.camera_id} controller is closed")
        
     # start thread
    def begin(self):
        if self.__camera.is_opened():
            self.start()
        else:
            self.__console.warning("Camera is not ready")
            
    # return camera id
    def __str__(self):
        return str(self.__camera.camera_id)
    
    # return single shot grabbed image
    def grab(self):
        return self.__camera.grab()
    
    # image grab with thread
    def run(self):
        while True:
            # if interrupt requested
            if self.isInterruptionRequested():
                break
            
            t_start = datetime.now()
            ret, frame = self.__camera.grab()

            if ret:                
                t_end = datetime.now()
                framerate = float(1./(t_end - t_start).total_seconds())

                self.frame_update_signal.emit(frame, framerate)

        
'''
Camera Finder to discover GigE Cameras (Basler)
'''   
def gige_camera_discovery() -> list:
    
    _caminfo_array:list = []
    
    # reset camera array
    global _camera_array_container
    if _camera_array_container != None:
        _camera_array_container.StopGrabbing()
        _camera_array_container.Close()
    
    try:
        # get the transport layer factory
        _tlf = pylon.TlFactory.GetInstance()
        
        # get all attached devices
        _devices = _tlf.EnumerateDevices()
        
        if len(_devices)==0:
            raise Exception(f"No camera present")
        
        # create camera array container
        _camera_array_container = pylon.InstantCameraArray(len(_devices))
        
        # create and attach all device
        for idx, cam in enumerate(_camera_array_container):
            cam.Attach(_tlf.CreateDevice(_devices[idx]))
            _model_name = cam.GetDeviceInfo().GetModelName()
            _ip_addr = _devices[idx].GetIpAddress()
            print(f"found GigE Camera Device {_model_name}({_ip_addr})")
            
            _caminfo_array.append((idx, _model_name, _ip_addr))
        
    except Exception as e:
        print(f"{e}")
        
    return _caminfo_array
    
'''
Camera container termination
'''
def gige_camera_destroy():
    global _camera_array_container
    if _camera_array_container:
        _camera_array_container.StopGrabbing()
        _camera_array_container.Close()