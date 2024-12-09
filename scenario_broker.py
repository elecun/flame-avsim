"""
Scenario Broker
"""

import subprocess
import sys
import os
import argparse
import json
import pathlib
import paho.mqtt.client as mqtt

from util.logger.console import ConsoleLogger
import subprocess


class command_broker:
    def __init__(self, host=str):
        self.__console = ConsoleLogger.get_logger()

        # message api
        self.message_api = {
            "flame/avsim/carla/process/mapi_launch": self.on_process_launch,
            "flame/avsim/carla/process/mapi_terminate": self.on_process_terminate
        }

        # MQTT Connections
        self.mq_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id="commad_broker", transport='tcp', protocol=mqtt.MQTTv311, clean_session=True)
        self.mq_client.on_connect = self.on_mqtt_connect
        self.mq_client.on_message = self.on_mqtt_message
        self.mq_client.on_disconnect = self.on_mqtt_disconnect
        self.mq_client.connect_async(host, port=1883, keepalive=60)
        # self.mq_client.loop_start()

        
    def on_mqtt_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code==0:
            for topic in self.message_api.keys():
                self.mq_client.subscribe(topic, 0)
            print("Connected to broker")
        else:
            print("Connection Failed")
        
    def on_mqtt_disconnect(self, mqttc, userdata, rc):
        print("disconnected")

    def on_mqtt_message(self, client, userdata, msg):
        mapi = str(msg.topic)

        # test
        self.run_command("python avsim_monitor.py --config avsim_monitor.cfg")
        
        try:
            if mapi in self.message_api.keys():
                payload = json.loads(msg.payload)          
                self.message_api[mapi](payload)
                self.__console.info(f"call mapi : {mapi}")
            else:
                self.__console.warning(f"Unknown Message API was called : {mapi}")

        except json.JSONDecodeError as e:
            self.__console.warning("Message API payload is not valid")

    def run_command(self, command):
        try:
            # subprocess.run으로 명령 실행
            result = subprocess.run(
                command,      # 실행할 명령 (리스트 형태로 전달)
                shell=True,   # 문자열 명령을 쉘을 통해 실행
                text=True,    # 출력을 문자열로 디코딩
                capture_output=True  # 출력 캡처
            )
            print("Return Code:", result.returncode)
            print("Standard Output:", result.stdout)
            print("Standard Error:", result.stderr)
        except Exception as e:
            print("Error:", e)


    def on_process_launch(self, command):
        """process run command with arguments """
        self.run_command(command)

    def on_process_terminate(self, command):
        """process terminate command with arguments """
        self.run_command(command)

    def loop_forever(self):
        self.mq_client.loop_forever()


if __name__=="__main__":

    try:
        broker = command_broker(host = "127.0.0.1")
        broker.loop_forever()
    except Exception as e:
        print(f"Error : {e}")
    except KeyboardInterrupt as e:
        print(f"Error : {e}")
    
    exit(1)