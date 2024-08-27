import os, sys
import cv2
import pathlib
import json
import paho.mqtt.client as mqtt

try:
    # using PyQt5
    from PyQt5.QtGui import QImage, QPixmap, QCloseEvent
    from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QMessageBox, QProgressBar, QFileDialog
    from PyQt5.uic import loadUi
    from PyQt5.QtCore import QObject, Qt, QTimer, QThread, pyqtSignal
except ImportError:
    # using PyQt6
    from PyQt6.QtGui import QImage, QPixmap, QCloseEvent, QStandardItem, QStandardItemModel, QIcon, QColor
    from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QMessageBox, QProgressBar, QFileDialog
    from PyQt6.uic import loadUi
    from PyQt6.QtCore import QModelIndex, QObject, Qt, QTimer, QThread, pyqtSignal


class ScenarioRunner(QTimer):

    scenario_start_slot = pyqtSignal(float, str, str) #arguments : time_key, mapi, message
    scenario_stop_slot = pyqtSignal()

    def __init__(self, interval_ms):
        super().__init__()
        self.time_interval = interval_ms # default interval_ms = 100ms
        self.setInterval(interval_ms)
        self.timeout.connect(self.on_timeout_callback) # timer callback
        self.current_time_idx = 0  # time index
        self.scenario_container = {} # scenario data container
        
        self._end_time = 0.0
    
    # reset all params    
    def initialize(self):
        self.current_time_idx = 0
        self.scenario_container.clear()
        
    # scenario running callback by timeout event
    def on_timeout_callback(self):
        time_key = round(self.current_time_idx, 1)
        if self._end_time<self.current_time_idx:
            self.scenario_stop_slot.emit()
        else:
            if time_key in self.scenario_container.keys():
                for msg in self.scenario_container[time_key]:
                    self.scenario_start_slot.emit(time_key, msg["mapi"], msg["message"])
            
        self.current_time_idx += self.time_interval/1000 # update time index
    
    # open & load scenario file
    def load_scenario(self, scenario:dict) -> bool:
        self.stop_scenario() # if timer is running, stop the scenario runner

        if len(scenario)<1:
            print("> Empty Scenario. Please check your scenario")
            return False
        
        try:
            if "scenario" in scenario:
                for scene in scenario["scenario"]:
                    self.scenario_container[scene["time"]] = [] # time indexed container
                    for event in scene["event"]: # for every events
                        self.scenario_container[scene["time"]].append(event) # append event
            self._end_time = max(list(self.scenario_container.keys()))

        except json.JSONDecodeError as e:
            print("JSON Decode error", str(e))
            return False

        return True
    
    # start timer
    def run_scenario(self):
        if self.isActive(): # if the timer is now active(=running)
            self.stop() # stop the timer
        self.start() # then restart the timer
    
    # stop timer
    def stop_scenario(self):
        self.current_time_idx = 0 # timer index set 0
        self.stop() # timer stop
        
    # pause timer
    def pause_scenario(self):
        self.stop() # stop the timer, but timer index does not set 0