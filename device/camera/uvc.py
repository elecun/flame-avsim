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
from device.camera.interface import ICamera
import numpy as np
from typing import Tuple
import csv
import pathlib


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
    def get_properties(self) ->Tuple[float, int, int]:
        fps = self.__grabber.get(cv2.CAP_PROP_FPS)
        w = int(self.__grabber.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self.__grabber.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return (fps, w, h)

# camera controller class
class Controller(QThread):

    frame_update_signal = pyqtSignal(int, np.ndarray, float) # camera_id, image_frame, framerate

    def __init__(self, camera_id:int):
        super().__init__()
        
        self.__console = ConsoleLogger.get_logger()   # console logger
        self.__uvc_camera = UVC(camera_id)    # UVC camera device
        self.__raw_video_writer = None      # camera video writer
        self.__recording_released = False
        self.__is_recording = False # video recording status
        self.__prev_timestamp = datetime.now() # previous timestamp
        self.__timestamp_writer = None
        self.__timestamp_file = None
    
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
    def get_pixel_resolution(self) -> Tuple[int, int]:
        fps, w, h = self.__uvc_camera.get_properties()
        return (w,h)
    
    # camera framerate
    def get_framerate(self) -> float:
        fps, _, _ = self.__uvc_camera.get_properties()
        return fps
    
    # get camera properties
    def get_properties(self) -> Tuple[float, int, int]:
        return self.__uvc_camera.get_properties()
    
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
            
            t_current = datetime.now()
            ret, frame = self.__uvc_camera.grab()

            if ret:                
                # t_end = datetime.now()
                framerate = float(1./(t_current - self.__prev_timestamp).total_seconds())
                self.frame_update_signal.emit(self.__uvc_camera.get_camera_id(), frame, framerate)
                self.__prev_timestamp = t_current

                # record video
                if self.__is_recording:
                    self.raw_video_record_with_timestamp(frame, t_current)
                else:
                    if self.__recording_released:
                        self.release_video_writer()
                        self.__recording_released = False
    
    def is_recording(self) -> bool:
        return self.__is_recording
    
    # video recording process impl.
    def raw_video_record(self, frame):
        if self.__raw_video_writer != None:
            self.__raw_video_writer.write(frame)

    # video recording with timestamp(csv)
    def raw_video_record_with_timestamp(self, frame, tstamp:datetime):
        if self.__raw_video_writer:
            self.__raw_video_writer.write(frame)
        if self.__timestamp_writer:
            self.__timestamp_writer.writerow([str(tstamp.timestamp())])

    # create new video writer to save as video file
    def create_raw_video_writer(self, workspace):
        if self.__is_recording:
            self.release_video_writer()
            self.__is_recording = False

        # define save path
        save_path = pathlib.Path(workspace)/pathlib.Path("camera")
        save_path.mkdir(parents=True, exist_ok=True)

        fps, w, h = self.__uvc_camera.get_properties()
        fourcc = cv2.VideoWriter_fourcc(*'MJPG') # low compression but bigger (file extension : avi) MJPG, I420

        print(f"recording camera({self.__uvc_camera.get_camera_id()}) info : ({w},{h}@{fps})")
        self.__raw_video_writer = cv2.VideoWriter((save_path/pathlib.Path(f"cam_{self.__uvc_camera.get_camera_id()}.avi")).as_posix(), fourcc, 30, (w, h)) # 30fps

        # timestamp log to csv
        self.__timestamp_file = open((save_path/f"timestamp_{self.__uvc_camera.get_camera_id()}.csv"), mode='w')
        self.__timestamp_writer = csv.writer(self.__timestamp_file)

    # destory the video writer
    def release_video_writer(self):
        self.__timestamp_file.flush()
        self.__timestamp_file.close()

        if self.__raw_video_writer:
            self.__raw_video_writer.release()
            self.__console.info("Recorder is completely released")
            self.__raw_video_writer = None
        

    # start video recording (workspace : path to save)
    def start_recording(self, workspace):
        if not self.__is_recording:
            self.create_raw_video_writer(workspace)
            self.__is_recording = True # working on thread

    # stop video recording
    def stop_recording(self):
        if self.__is_recording:
            self.__recording_released = True
            self.__is_recording = False

