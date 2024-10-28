'''
Show AVI Information
@auhtor Byunghun Hwang<bh.hwnag@iae.re.kr>
'''

import sys, os
import pathlib
import json
from datetime import datetime
import argparse
import time
import cv2

from util.logger.console import ConsoleLogger


if __name__ == "__main__":

    console = ConsoleLogger.get_logger()

    # arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', nargs='?', required=True, help="Video File(*.avi)")
    args = parser.parse_args()
    
    try:

        target_file = pathlib.Path(args.file)
        console.info(f"Target File : {target_file.as_posix()}")

        target = cv2.VideoCapture(target_file.as_posix()) # load target video file
        if not target.isOpened():
            console.error(f"Could not open video file.")
        else:
            total_frames = int(target.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = target.get(cv2.CAP_PROP_FPS)
            
            print("================================")
            print(f"File : {target_file.as_posix()}")
            print(f"Total Frames : {total_frames}")
            print(f"FPS : {fps}")
            print(f"Duration : {total_frames/fps}")
            print("================================")

            target.release()
        


    except Exception as e:
        console.critical(f"{e}")