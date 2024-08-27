'''
YOLOv8 Human Pose Estimation Process Class
@author Byunghun Hwang<bh.hwang@iae.re.kr>
'''


from ultralytics import YOLO
import pathlib
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal
import cv2

from util.logger.console import ConsoleLogger
from hpe.iestimator import IVisionEstimator

class PoseModel(QObject):
    
    estimated_result_image = pyqtSignal(np.ndarray)
    estimated_result_kpt = pyqtSignal(list)
    
    def __init__(self, modelname:str, id:int) -> None:
        super().__init__()
        
        self.__console = ConsoleLogger.get_logger()
        
        self.__id = id
        
        pretrained_path = pathlib.Path(__file__).parent / "pretrained"
        self.__console.info(f"Load model in {pretrained_path.as_posix()}")
        self.__is_processing = False
        self.__pose_model = None
        
        try:
            if modelname.lower() == "yolov8n-pose.pt":
                self.__pose_model = YOLO(model=(pretrained_path / "yolov8n-pose.pt").as_posix())
            elif modelname.lower() == "yolov8s-pose.pt":
                self.__pose_model = YOLO(model=(pretrained_path / "yolov8s-pose.pt").as_posix())
            elif modelname.lower() == "yolov8m-pose.pt":
                self.__pose_model = YOLO(model=(pretrained_path / "yolov8m-pose.pt").as_posix())
            elif modelname.lower() == "yolov8l-pose.pt":
                self.__pose_model = YOLO(model=(pretrained_path / "yolov8l-pose.pt").as_posix())
            elif modelname.lower() == "yolov8x-pose.pt":
                self.__pose_model = YOLO(model=(pretrained_path / "yolov8x-pose.pt").as_posix())
            elif modelname.lower() == "yolov8x-pose-p6.pt":
                self.__pose_model = YOLO(model=(pretrained_path / "yolov8x-pose-p6.pt").as_posix())
            else:
                self.__console.warning("Unsupported HPE Model")
        except Exception as e:
            self.__console.critical(f"{e}")
            
    # get id
    def get_id(self) -> int:
        return self.__id
    
    # hpe prediction    
    def predict(self, image:np.ndarray, fps:float):
        if self.__is_processing:
            results = self.__pose_model.predict(image, iou=0.7, conf=0.7, verbose=False)
            
            # draw keypoints on image
            if len(results[0].boxes)>0:
                log_kps = []
                for kps in results[0].keypoints.xy.tolist(): #for multi-person
                    for kp in kps:
                        cv2.circle(image, center=(int(kp[0]), int(kp[1])), radius=7, color=(255,0,0), thickness=-1)
                        log_kps = log_kps + kp
            
                self.estimated_result_image.emit(image)
                self.estimated_result_kpt.emit(log_kps)
            
    
    # start pose estimating
    def start(self):
        self.__is_processing = True
    
    # stop pose estimating
    def stop(self):
        self.__is_processing = False
        
    
    