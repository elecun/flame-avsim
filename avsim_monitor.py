'''
flame-avsim monitoring & data ingestion application
@auhtor Byunghun Hwang<bh.hwnag@iae.re.kr>
'''

import sys, os
from PyQt6 import QtGui
import pathlib
import json
from PyQt6.QtGui import QImage, QPixmap, QCloseEvent
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QMessageBox
from PyQt6.uic import loadUi
from PyQt6.QtCore import QObject, Qt, QTimer, QThread, pyqtSignal
from datetime import datetime
import argparse
import time

# root directory registration on system environment
ROOT_PATH = pathlib.Path(__file__).parent
PROJECT_NAME = pathlib.Path(__file__).parent.stem
sys.path.append(ROOT_PATH.as_posix())

from avsim_monitor.window import AppWindow
from util.logger.console import ConsoleLogger


if __name__ == "__main__":

    console = ConsoleLogger.get_logger()

    # arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', nargs='?', required=False, help="Configuration File(*.cfg)", default="avsim_monitor.cfg")
    args = parser.parse_args()
    
    try:
        with open(args.config, "r") as cfile:
            configure = json.load(cfile)

            # set hidden configurations
            configure["root_path"] = ROOT_PATH
            configure["app_path"] = ROOT_PATH / "avsim_monitor"

            console.info(f"* ROOT Path : {configure['root_path']}")
            console.info(f"* App Path : {configure['app_path']}")


            app = QApplication(sys.argv)
            app_window = AppWindow(config=configure)
            
            if "app_window_title" in configure:
                app_window.setWindowTitle(configure["app_window_title"])
            app_window.show()
            sys.exit(app.exec())

    except json.JSONDecodeError as e:
        console.critical(f"Configuration File Load Error : {e}")
    except Exception as e:
        console.critical(f"{e}")
        
    
        
    