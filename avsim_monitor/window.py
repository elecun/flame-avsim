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
from datetime import datetime
from pygame import mixer
import csv

try:
    # using PyQt5
    from PyQt5.QtGui import QImage, QPixmap, QCloseEvent
    from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QMessageBox, QProgressBar, QFileDialog, QLineEdit
    from PyQt5.uic import loadUi
    from PyQt5.QtCore import QObject, Qt, QTimer, QThread, pyqtSignal
except ImportError:
    # using PyQt6
    from PyQt6.QtGui import QImage, QPixmap, QCloseEvent, QStandardItem, QStandardItemModel, QIcon, QColor
    from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QMessageBox, QProgressBar, QFileDialog, QLineEdit
    from PyQt6.uic import loadUi
    from PyQt6.QtCore import QModelIndex, QObject, Qt, QTimer, QThread, pyqtSignal

from util.logger.console import ConsoleLogger
from avsim_monitor.scenario_runner import ScenarioRunner
from device.eyetracker.neon import neon_controller
from device.camera.uvc import Controller as camera_controller

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
                self.actionOpen_operating_scenario.triggered.connect(self.on_scenario_open)
                self.btn_eyetracker_discovery.clicked.connect(self.on_eyetracker_discovery)
                self.btn_eyetracker_record.clicked.connect(self.on_eyetracker_record)
                self.btn_eyetracker_stop.clicked.connect(self.on_eyetracker_stop)
                self.table_sound_files.doubleClicked.connect(self.on_dbclick_sound_select) # play selected sound file
                self.btn_camera_record.clicked.connect(self.on_camera_record_start)
                self.btn_camera_record_stop.clicked.connect(self.on_camera_record_stop)
                self.btn_sound_stop.clicked.connect(self.on_sound_stop)

                # map between camera device and windows
                self.__frame_window_map = {}
                self.__camera_device_map = {}
                for idx, id in enumerate(config["camera_ids"]):
                    self.__frame_window_map[id] = self.findChild(QLabel, config["camera_windows"][idx])
                    self.__camera_device_map[id] = camera_controller(id)
                    if self.__camera_device_map[id].open(): # ok
                        self.__camera_device_map[id].frame_update_signal.connect(self.on_camera_frame_update)
                        if "camera_startup" in config:
                            if config["camera_startup"]:
                                self.__camera_device_map[id].begin()
                    else:
                        self.__camera_device_map[id].close()
                        del self.__camera_device_map[id]

                # scenario model
                self.scenario_table_columns = ["Time(s)", "Message API", "Payload"]
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
                for topic in config["subscribe_topics"]:
                    self.__console.info(f"subscribe topic : {topic}")

                # simulation scenario runner
                self.runner = ScenarioRunner(interval_ms=100)
                self.runner.scenario_start_slot.connect(self.do_scenario_process)
                self.runner.scenario_stop_slot.connect(self.end_scenario_process)

                # eyetracker device discovery
                self.__eyetracker = None
                if config["use_eyetracker"]:
                    self.__eyetracker = neon_controller(config)
                    self.__eyetracker.status_update_signal.connect(self.on_eyetracker_status_update)
                    self.__eyetracker.device_discover()

                # load sound resource
                mixer.init()
                sound_path = pathlib.Path(self.config["root_path"])/pathlib.Path(self.config["sound_resource_path"])
                self.sound_files = list(sound_path.glob(f"*.mp3"))
                self.__resource_sound = {}
                sound_resource_table_columns = ["Sound Resources"]
                self.__sound_resource_model = QStandardItemModel()
                self.__sound_resource_model.setColumnCount(len(sound_resource_table_columns))
                self.__sound_resource_model.setHorizontalHeaderLabels(sound_resource_table_columns)
                self.table_sound_files.setModel(self.__sound_resource_model)
                self.on_load_sound_resource()
                
                # message APIs
                self.message_api = {
                    "flame/avsim/cabinview/nback/log": self.mapi_nback_log,
                    "flame/avsim/camera/record/start": self.mapi_camera_record_start,
                    "flame/avsim/eyetracker/record/start": self.mapi_eyetracker_record_start,
                    "flame/avsim/mixer/mapi_play": self.mapi_sound_play, # sound play
                    "flame/avsim/mixer/mapi_stop": self.mapi_sound_stop, # sound stop
                }

                # log files & writer
                self.nback_logfile = None
                self.nback_logfile_writer = None
                self.scenario_logfile = None
                self.scenario_logfile_writer = None
                

        except Exception as e:
            self.__console.critical(f"{e}")

    # terminate main window
    def closeEvent(self, event:QCloseEvent) -> None: 
        self.__console.info("Window is now terminated")

        if self.__eyetracker:
            self.__eyetracker.close()

        for camera in self.__camera_device_map.values():
            camera.close()

        # close log file
        if self.nback_logfile:
            self.nback_logfile.flush()
            self.nback_logfile.close()

        if self.scenario_logfile:
            self.scenario_logfile.flush()
            self.scenario_logfile.close()
            
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
                self.runner.load_scenario(scenario_data)
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
        
        # stamp time
        tstamp = datetime.now()
        if self.scenario_logfile_writer:
            self.scenario_logfile_writer.writerow([str(tstamp.timestamp()), "scenario start"])
            self.scenario_logfile.flush()
        
        # show start timestamp
        self.label_simulation_start_at.setText(tstamp.strftime("%Y-%m-%d %H:%M:%S"))

        self.__scenario_mark_row_reset()
        self.runner.run_scenario()
        self.on_camera_record_start() # camera record start
        self.on_eyetracker_record() # eyetracker record start
        self.__show_on_statusbar("Scenario is now running...")

    '''
    Scenario Stop Event Callback Function
    '''
    def on_scenario_stop(self):

        # stamp time
        tstamp = datetime.now()
        if self.scenario_logfile_writer:
            self.scenario_logfile_writer.writerow([str(tstamp.timestamp()), "scenario end"])
            self.scenario_logfile.flush()

        # show start timestamp
        self.label_simulation_end_at.setText(tstamp.strftime("%Y-%m-%d %H:%M:%S"))

        self.runner.stop_scenario()
        self.on_eyetracker_stop() # eyetracker record stop
        self.on_camera_record_stop() # camera record stop
        self.__show_on_statusbar("Scenario is stopped.")

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
    def __scenario_mark_row_color(self, row):
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
        for topic in self.config["subscribe_topics"]:
            self.mq_client.subscribe(topic, 2)
        self.__show_on_statusbar("Connected to Broker({})".format(str(rc)))
        
    def on_mqtt_disconnect(self, mqttc, userdata, rc):
        self.__show_on_statusbar("Disconnected to Broker({})".format(str(rc)))

    def on_mqtt_message(self, mqttc, userdata, msg):
        mapi = str(msg.topic)
        
        try:
            if mapi in self.message_api.keys():
                payload = json.loads(msg.payload)          
                self.message_api[mapi](payload)
                self.__console.info(f"call mapi : {mapi}")
            else:
                self.__console.warning(f"Unknown Message API was called : {mapi}")

        except json.JSONDecodeError as e:
            self.__console.warning("Message API payload is not valid")

    '''
    enroll new subject button click event callback
    '''
    def on_new_subject(self):
        subject_name = self.findChild(QLineEdit, name="edit_subject_name").text()
        target_path = pathlib.Path(self.config["root_path"])/pathlib.Path(self.config["save_path"])/pathlib.Path(subject_name)/pathlib.Path(datetime.now().strftime("%Y-%m-%d-%H-%M-%S"))
        self.config["target_workspace"] = target_path.as_posix()
        self.config["target_name"] = subject_name
        os.makedirs(target_path, exist_ok=True)
        self.label_simulation_data_path.setText(target_path.as_posix())
        self.__show_on_statusbar(f"Created {target_path.as_posix()}")

        # create logfile (nback task)
        self.nback_logfile = open(target_path/"nback_response.csv", "a")
        self.nback_logfile_writer = csv.writer(self.nback_logfile)

        # create logfile (scenario)
        self.scenario_logfile = open(target_path/"scenario_history.csv", "a")
        self.scenario_logfile_writer = csv.writer(self.scenario_logfile)

        # initialize
        self.label_simulation_start_at.setText("")
        self.label_simulation_end_at.setText("")


    def do_scenario_process(self, time, mapi, message):
        message = message.replace("'", '"')
        self.mq_client.publish(mapi, message, 2) # publish mapi interface

        self.__scenario_mark_row_reset()
        for row in range(self.scenario_model.rowCount()):
            if time == float(self.scenario_model.item(row, 0).text()):
                self.__scenario_mark_row_color(row)


    '''
    End of simulation scenario (call scenario runner reaches the end of the time index)
    '''
    def end_scenario_process(self):
        self.on_scenario_stop()
        QMessageBox.information(self, "Scenario", "End")


    # eyetracker status update
    def on_eyetracker_status_update(self, status:dict):
        self.label_eyetracker_ip.setText(status["address"])
        self.label_eyetracker_name.setText(status["name"])
        self.label_eyetracker_battery_level.setText(str(status["battery_level"]))
        self.label_eyetracker_battery_state.setText(status["battery_state"])
        self.label_eyetracker_free_storage.setText(f"{status['free_storage']:.1f}GB")
        self.label_eyetracker_memory_state.setText(status["memory_state"])

    # show camera grabbed image
    def on_camera_frame_update(self, camera_id, frame, fps):
        frame_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        t = datetime.now()
        cv2.putText(frame_image, t.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3], (10, 1070), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0,255,0), 2, cv2.LINE_AA)
        cv2.putText(frame_image, f"Camera #{camera_id}(fps:{fps:.1f})", (10,50), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (1,255,0), 2, cv2.LINE_AA)

        h, w, ch = frame_image.shape
        qt_image = QImage(frame_image.data, w, h, ch*w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        try:
            self.__frame_window_map[camera_id].setPixmap(pixmap.scaled(self.__frame_window_map[camera_id].size(), Qt.AspectRatioMode.KeepAspectRatio))
        except Exception as e:
            self.__console.error(e)


    # eyetracker custom event callback
    def on_eyetracker_discovery(self):
        self.__eyetracker.device_discover()
    def on_eyetracker_record(self):
        self.__eyetracker.record_start()
    def on_eyetracker_stop(self):
        self.__eyetracker.record_stop()

    # sound mixer
    def on_load_sound_resource(self):
        self.__sound_resource_model.setRowCount(0)
        for resource in self.sound_files:
            self.__sound_resource_model.appendRow([QStandardItem(str(resource.name))])
            self.__resource_sound[resource.name] = mixer.Sound(str(resource))
        self.table_sound_files.resizeColumnsToContents()
    
    def sound_play(self, filename:str, volume:float=1.0):
        if filename in self.__resource_sound.keys():
            self.__resource_sound[filename].set_volume(volume)
            self.__resource_sound[filename].play()
            # row_index = self.resource_model.findItems(filename, Qt.MatchFlag.MatchExactly, 0)[0].row()

    def on_dbclick_sound_select(self):
        row = self.table_sound_files.currentIndex().row()

        if self.sound_files[row].name in self.__resource_sound.keys():
            self.__currnet_playing_sound = self.sound_files[row].name
            self.__resource_sound[self.__currnet_playing_sound].play()
            self.sound_play(self.__currnet_playing_sound)

    def on_sound_stop(self):
        if self.__currnet_playing_sound:
            if self.__currnet_playing_sound in self.__resource_sound.keys():
                self.__resource_sound[self.__currnet_playing_sound].stop()
        

    # camera record control
    def on_camera_record_start(self):
        for camera in self.__camera_device_map.values():
            self.__console.info(f"Start Recording (ID : {camera.get_camera_id()}")
            camera.start_recording(self.config["target_workspace"])

    def on_camera_record_stop(self):
        for camera in self.__camera_device_map.values():
            self.__console.info(f"Stop recording (ID:{camera.get_camera_id()})")
            camera.stop_recording()
            
    
    # nback log via message api
    def mapi_nback_log(self, payload:dict):
        if self.nback_logfile_writer:
            self.nback_logfile_writer.writerow([payload["timestamp"], payload["message"]])
            self.nback_logfile.flush()

    # camera record start via message api
    def mapi_camera_record_start(self, payload:dict):
        self.__console.info("camera record start")
    
    # eyetracker record start via message api
    def mapi_eyetracker_record_start(self, payload:dict):
        self.__console.info("eyetracker record start")

    # sound play via message api
    def mapi_sound_play(self, payload:dict):
        self.sound_play(payload["file"], payload["volume"])

    # sound stop via message api
    def mapi_sound_stop(self, payload:dict):
        self.on_sound_stop()