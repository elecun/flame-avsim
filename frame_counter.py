'''
Dataset Frame Counter
'''

import argparse
import sys, os
import pathlib
import cv2
from openpyxl import Workbook

from util.logger.console import ConsoleLogger

def get_video_info(video_path):
    """Gets frame rate and total frame count of a video file."""
    try:
        video = cv2.VideoCapture(video_path)
        fps = video.get(cv2.CAP_PROP_FPS)
        total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))

        #Check for invalid frame counts (sometimes reported as 0)
        if total_frames <=0 :
          total_frames = count_frames(video)

        video.release()
        return fps, total_frames
    except Exception as e:
        print(f"Error processing {video_path}: {e}")
        return None, None

def count_frames(video):
    """Counts frames if metadata is unavailable or unreliable."""
    count = 0
    while True:
        ret, _ = video.read()
        if not ret:
            break
        count += 1
    return count



def find_and_get_info(directory):
    """Finds AVI and MP4 files and gets their frame rates and total frame counts."""
    results = {}
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(('.avi', '.mp4')):
                video_path = os.path.join(root, file)
                fps, total_frames = get_video_info(video_path)
                if fps is not None and total_frames is not None:
                    results[video_path] = {'fps': fps, 'total_frames': total_frames}
    return results

if __name__ == "__main__":
    console = ConsoleLogger.get_logger()

    # arguments
    parser = argparse.ArgumentParser(description="Get frame rates of video file in a directory")
    parser.add_argument('--path', nargs='?', required=True, help="Dataset Path", default="/mnt/avsim_nas")
    parser.add_argument('--out', nargs='?', required=True, help="Output Filename(*.xlsx)", default="result.xlsx")
    args = parser.parse_args()

    video_info = find_and_get_info(args.path)

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Video File", "Frame Rate", "Total Frames"])  # Header row

    if video_info:
        for video_path, info in video_info.items():
            sheet.append([video_path, info['fps'], info['total_frames']])

    workbook.save(args.out)
    print(f"Saved {args.out}")

    try:
        pass
    except Exception as e:
        console.critical(f"{e}")