'''
Vision Estimator Abstract Class
@author Byunghun Hwang<bh.hwang@iae.re.kr>
'''

from abc import ABC, abstractmethod
import numpy as np

class IVisionEstimator(ABC):
    def __init__(self, name:str) -> None:
        super().__init__()
        self.__name = name
    
    @abstractmethod
    def predict(self, image:np.ndarray, fps:float):
        pass
    
    # estimator name
    def get_name(self):
        return self.__name