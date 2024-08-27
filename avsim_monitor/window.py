'''
Appication Window GUI
@author Byunghun Hwang<bh.hwang@iae.re.kr>
'''

import os, sys
import cv2
import pathlib
import json
import time
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

from util.logger.console import ConsoleLogger
from avsim_monitor.scenario_runner import ScenarioRunner
from device.eyetracker.neon import neon_controller

'''
Application Window class
'''
class AppWindow(QMainWindow):
    def __init__(self, config:dict):
        super().__init__()

        self.__console = ConsoleLogger.get_logger()
        self.config = config

        try:            
            if "gui" in config:

                # load gui file
                ui_path = pathlib.Path(config["app_path"]) / config["gui"]
                if os.path.isfile(ui_path):
                    loadUi(ui_path, self)
                else:
                    raise Exception(f"Cannot found UI file : {ui_path}")
                
                # register event callback function
                self.btn_scenario_open.clicked.connect(self.on_scenario_open)
                self.btn_scenario_start.clicked.connect(self.on_scenario_start)
                self.btn_scenario_stop.clicked.connect(self.on_scenario_stop)
                self.btn_new_subject.clicked.connect(self.on_new_subject)
                self.btn_camera_connect_all.clicked.connect(self.on_camera_connect_all)

                # map between camera device and windows
                self.__frame_window_map = {}
                for idx, id in enumerate(config["camera_ids"]):
                    self.__frame_window_map[id] = config["camera_windows"][idx]

                # scenario model
                self.scenario_table_columns = ["Time(s)", "MAPI", "Message"]
                self.scenario_model = QStandardItemModel()
                self.scenario_model.setColumnCount(len(self.scenario_table_columns))
                self.scenario_model.setHorizontalHeaderLabels(self.scenario_table_columns)
                self.table_scenario_contents.setModel(self.scenario_model)

                # MQTT Connections
                self.mq_client = mqtt.Client(client_id="avsim_monitor", transport='tcp', protocol=mqtt.MQTTv311, clean_session=True)
                self.mq_client.on_connect = self.on_mqtt_connect
                self.mq_client.on_message = self.on_mqtt_message
                self.mq_client.on_disconnect = self.on_mqtt_disconnect
                self.mq_client.connect_async(config["broker_ip"], port=1883, keepalive=60)
                self.mq_client.loop_start()

                # simulation scenario runner
                self.runner = ScenarioRunner(interval_ms=100)
                self.runner.scenario_start_slot.connect(self.do_scenario_process)
                self.runner.scenario_stop_slot.connect(self.end_scenario_process)

                # eyetracker device discovery
                if config["use_eyetracker"]:
                    self.__console.info("Discovering eyetracker...")
                    self.__eyetracker = neon_controller(5)
                    self.__eyetracker.status_update_signal.connect(self.on_eyetracker_status_update)
                    self.__eyetracker.start()


        except Exception as e:
            self.__console.critical(f"{e}")

    # terminate main window
    def closeEvent(self, event:QCloseEvent) -> None: 
        self.__console.info("Window is now terminated")

        if self.config["use_eyetracker"]:
            if self.__eyetracker.is_working():
                self.__eyetracker.stop()
                self.__eyetracker.wait()

        #self.cameraWindow.close()
        #self.close()
        return super().closeEvent(event)

    '''
    Scenario Open Evnet Callback Function
    '''
    def on_scenario_open(self):
        selected_file = QFileDialog.getOpenFileName(self, 'Open scenario file', './')
        if selected_file[0]:
            sfile = open(selected_file[0], "r")
            self.scenario_filepath = selected_file[0]
            
            with sfile:
                try:
                    scenario_data = json.load(sfile)
                except Exception as e:
                    QMessageBox.critical(self, "Error", "Scenario file read error {}".format(str(e)))
                    
                # parse scenario file
                #self.runner.load_scenario(scenario_data)
                self.scenario_model.setRowCount(0)
                if "scenario" in scenario_data:
                    for data in scenario_data["scenario"]:
                        for event in data["event"]:
                            self.scenario_model.appendRow([QStandardItem(str(data["time"])), QStandardItem(event["mapi"]), QStandardItem(event["message"])])

                # table view column width resizing
                self.table_scenario_contents.resizeColumnsToContents()
    
    '''
    Scenario Start Event Callback Function
    '''
    def on_scenario_start(self):
        self.__scenario_mark_row_reset()
        #self.runner.run_scenario()
        self.__show_on_statusbar("Simulation Scenario is now running...")

    '''
    Scenario Stop Event Callback Function
    '''
    def on_scenario_stop(self):
        #self.runner.stop_scenario()
        self.__show_on_statusbar("Simulation Scenario is stopped.")

    '''
    Scenario table mark row reset
    '''
    def __scenario_mark_row_reset(self):
        for col in range(self.scenario_model.columnCount()):
            for row in range(self.scenario_model.rowCount()):
                self.scenario_model.item(row,col).setBackground(QColor(0,0,0,0))

    '''
    Scenario table mark colored
    '''
    def __scenario_makr_row_color(self, row):
        for col in range(self.scenario_model.columnCount()):
            self.scenario_model.item(row,col).setBackground(QColor(255,0,0,100))

    '''
    show string on status bar
    '''
    def __show_on_statusbar(self, text):
        self.statusBar().showMessage(text)

    '''
    MQTT event callback
    '''
    def on_mqtt_connect(self, mqttc, obj, flags, rc):
        # subscribe message api
        for topic in self.message_api.keys():
            self.mq_client.subscribe(topic, 0)
        
        self.__show_on_statusbar("Connected to Broker({})".format(str(rc)))
        
    def on_mqtt_disconnect(self, mqttc, userdata, rc):
        self.__show_on_statusbar("Disconnected to Broker({})".format(str(rc)))

    def on_mqtt_message(self, mqttc, userdata, msg):
        mapi = str(msg.topic)
        
        try:
            if mapi in self.message_api.keys():
                payload = json.loads(msg.payload)
                if "app" not in payload:
                    print("message payload does not contain the app")
                    return
                
                if payload["app"] != "avsim_monitor":
                    self.message_api[mapi](payload)
            else:
                print("Unknown MAPI was called :", mapi)

        except json.JSONDecodeError as e:
            print("MAPI Message payload cannot be converted")

    '''
    enroll new subject button click event callback
    '''
    def on_new_subject(self):
        pass

    '''
    camera connection button click event callback
    '''
    def on_camera_connect_all(self):
        pass

    def do_scenario_process(self, time, mapi, message):
        message.replace("'", "\"")
        #self.mq_client.publish(mapi, message, 0) # publish mapi interface

        self.__scenario_mark_row_reset()
        for row in range(self.scenario_model.rowCount()):
            if time == float(self.scenario_model.item(row, 0).text()):
                self.__scenario_makr_row_color(row)

    '''
    scenario end
    '''
    def __end_scenario(self):
        self.runner.stop_scenario()
        self.__show_on_statusbar("Scenario runner works done")
        QMessageBox.information(self, "Scenario", "End")

    '''
    End of simulation scenario
    '''
    def end_scenario_process(self):
        self.__end_scenario()


    # eyetracker status update
    def on_eyetracker_status_update(self, status:dict):
        self.label_eyetracker_ip = status["address"]
        self.label_eyetracker_name = status["name"]
        self.label_eyetracker_battery_level = status["batter_level"]
        self.label_eyetracker_battery_state = status["battery_state"]
        self.label_eyetracker_free_storage = status["free_storage"]
        self.label_eyetracker_memory_state = status["memory_state"]