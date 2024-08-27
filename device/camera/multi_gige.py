'''
Gigabit Ethernet interface multi camera device class
@Author <bh.hwang@iae.re.kr>
'''

try:
    from PyQt5.QtCore import QObject, Qt, QTimer, QThread, pyqtSignal
    from PyQt5.QtGui import QImage
except ImportError:
    from PyQt6.QtCore import QObject, Qt, QTimer, QThread, pyqtSignal
    from PyQt6.QtGui import QImage
    
    
from datetime import datetime
from util.logger.video import VideoRecorder
from util.logger.console import ConsoleLogger
import numpy as np
from pypylon import genicam
from pypylon import pylon
import threading
import time

#(Note) acA1300-60gc = 125MHz(PTP disabled), 1 Tick = 8ns
#(Note) a2A1920-51gmPRO = 1GHZ, 1 Tick = 1ns
CAMERA_TICK_TIME = 1

# global variable for camera array
_camera_array_container:pylon.InstantCameraArray = None



# camera controller class
class Controller(QThread):
    
    frame_update_signal = pyqtSignal(int, np.ndarray, float) # to gui and process
    frame_update_signal_multi = pyqtSignal(int, dict, float)
    frame_write_signal = pyqtSignal(int, np.ndarray, float) # to write image/video
    
    def __init__(self):
        super().__init__()

        self.grab_termination_event = threading.Event() # for termination
        self.grab_thread = threading.Thread(target=self.grab, args =(self.grab_termination_event, ))

        self.rec_termination_event = threading.Event()
        self.recorder1_thread = threading.Thread(target=self.record1, args = (self.rec_termination_event, ))

        self.__converter = pylon.ImageFormatConverter()
        self.__converter.OutputPixelFormat = pylon.PixelType_BGR8packed
        self.__converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned
        
        self.__console = ConsoleLogger.get_logger()
        
    # getting camera id
    def get_num_camera(self) -> int:
        return _camera_array_container.GetSize()
    
    # camera open
    def open(self) -> bool:
        try:
            if not _camera_array_container.GetSize()>0:
                raise Exception(f"No camera present")
            else:
                self.grab_thread.start() # thread start
                return True
        except Exception as e:
            self.__console.critical(f"{e}")
        return False
    
    # camera close
    def close(self) -> None:

        self.requestInterruption() # to quit for thread
        self.quit()
        self.wait(1000)

        # grab thread termination
        self.grab_termination_event.set()
        self.grab_thread.join()

        _camera_array_container.Close()
        self.__console.info(f"Multi camera controller is closed")

    def record1(self, evt):
        while True:
            time.sleep(0.01)
            if evt.is_set():
                break

    # grab image
    def grab(self, evt):
        _camera_array_container.StartGrabbing(pylon.GrabStrategy_LatestImages, pylon.GrabLoop_ProvidedByUser)
        #_camera_array_container.StartGrabbing(pylon.GrabStrategy_OneByOne, pylon.GrabLoop_ProvidedByUser)
        #_camera_array_container.StartGrabbing(pylon.GrabStrategy_UpcomingImage, pylon.GrabLoop_ProvidedByUser)
        #_camera_array_container.StartGrabbing(pylon.GrabStrategy_LatestImages, pylon.GrabLoop_ProvidedByUser)
        multi_camera_fps = {}

        __raw_images = {}

        while True:

            if self.isInterruptionRequested():
                break

            t_start = datetime.now()
            grab_image = _camera_array_container.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
            camera_id = grab_image.GetCameraContext()

            if grab_image.GrabSucceeded():
                #img = grab_image.GetArray()
                image = self.__converter.Convert(grab_image)
                raw_image = image.GetArray()

                __raw_images[camera_id] = raw_image

                if camera_id in multi_camera_fps.keys():
                    framerate = float(1./(t_start - multi_camera_fps[camera_id]).total_seconds())
                else:
                    framerate = 0
                multi_camera_fps[camera_id] = t_start
                
                
                # send image
                #self.frame_update_signal.emit(camera_id, raw_image, framerate)
                if len(__raw_images)==10:
                    self.frame_update_signal_multi.emit(camera_id, __raw_images.copy(), framerate)
                    #self.__console.info(f"emit")
                    __raw_images.clear()

                time.sleep(0.001)
                if evt.is_set():
                    break

    # start grabbing thread
    def start_grab(self):
        self.grab_thread.start()
            
    # return camera id
    def __str__(self):
        return str(self.__camera.camera_id)

        
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

            # cam.Open()
            # cam.AcqusitionFrameRate.SetValue(10)
            # cam.AcquisitionFrameRateEnable.SetValue('On')
            # cam.TriggerMode.SetValue("On")
            # cam.TriggerDelay.SetValue(0)
            # cam.TriggerSelector.SetValue('FrameStart')
            # cam.TriggerSource.SetValue('Line2')
            # cam.TriggerActivation.SetValue('RisingEdge')
            # cam.Close()

            _model_name = cam.GetDeviceInfo().GetModelName()
            uid = cam.GetDeviceInfo().GetUserDefinedName()
            _ip_addr = _devices[idx].GetIpAddress()
            
            # _devices[idx].GetHeartbeatTimeout.SetValue(5000) # set timeout
            print(f"found GigE Camera Device (User ID:{uid}) {_model_name}({_ip_addr})")
            
            _caminfo_array.append((uid, _model_name, _ip_addr))
        
    except Exception as e:
        print(f"Exception : {e}")
        
    return _caminfo_array
    
'''
Camera container termination
'''
def gige_camera_destroy():
    global _camera_array_container
    if _camera_array_container:
        _camera_array_container.StopGrabbing()
        _camera_array_container.Close()