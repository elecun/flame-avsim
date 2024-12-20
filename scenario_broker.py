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
import time

from util.logger.console import ConsoleLogger
import subprocess
import threading

class command_broker:
    def __init__(self, host:str):
        self.processes = {}
        self.__console = ConsoleLogger.get_logger()
        self.threads_container = []
        self.pid_banker = {}
        self.pid_idx = 0

        # message api
        self.message_api = {
            "flame/avsim/carla/process/mapi_launch": self.on_process_launch
            #"flame/avsim/carla/process/mapi_terminate": self.on_process_terminate
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
            self.__console.info(f"Connected to broker successfully")
        else:
            self.__console.warning(f"Connection failed")
        
    def on_mqtt_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        self.__console.warning(f"Connection lost")

    def on_mqtt_message(self, client, userdata, msg):
        mapi = str(msg.topic)
        self.__console.info(f"Message API : {mapi}")

        try:
            if mapi in self.message_api.keys():
                self.__console.info(f"Payload : {msg.payload}")
                payload = json.loads(msg.payload)
                self.message_api[mapi](payload)
                self.__console.info(f"Call mapi : {mapi}")
            else:
                self.__console.warning(f"Unknown Message API was called : {mapi}")

        except json.JSONDecodeError as e:
            self.__console.warning("Message API payload is not valid")

    # def loop_forever(self):
    #     self.mq_client.loop_forever()

    def run_command(self, command:str):
        self.pid_banker[command] = self.pid_idx
        thread = threading.Thread(target=self.do_command, args=(command, self.pid_idx))
        self.pid_idx = self.pid_idx+1

        self.threads_container.append(thread)
        thread.start()
        # thread.join()

    def do_command(self, command:str, process_id:int):
        try:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.processes[process_id] = process

            while True:
                output = process.stdout.readline()
                if process.poll() is not None:
                    self.__console.warning(f"poll is not None")
                    break
                if output:
                    self.__console.info(f"[Process {process_id}] {output.strip()}")

            error_output = process.stderr.read()
            if error_output:
                self.__console.error(f"{command} =  {error_output.strip()}")

            return_code = process.poll()
            self.__console.info(f"Process {process_id} ('{command}') exited with return code: {return_code}")
            self.pid_banker.pop(command)

        except Exception as e:
            self.__console.error(f"An error occurred while executing '{command}': {e}")
        finally:
            self.processes.pop(process_id, None)

    def terminate_process(self, process_id:int):
        """subprocess termination by force"""
        process = self.processes.get(process_id)
        if process:
            # process.terminate()
            self.__console.info(f"Process {process_id} terminated.")
        else:
            self.__console.info(f"No process with ID {process_id} is running.")
    
    def on_process_launch(self, payload:dict):
        """process run command with arguments """
        self.run_command(payload["command"])

    def on_process_terminate(self, payload:dict):
        """process terminate command with arguments """
        command = payload["command"]
        # find pid with command
        if command in self.pid_banker.keys():
            self.terminate_process(self.pid_banker[command])
            self.__console.info(f"Now terminating the process {self.pid_banker[command]}")

    def loop_forever(self):
        self.mq_client.loop_forever()

if __name__=="__main__":
    
    console = ConsoleLogger.get_logger()

    parser = argparse.ArgumentParser()
    parser.add_argument('--host', nargs='?', required=True, help="Broker IP Address", default="127.0.0.1")
    args = parser.parse_args()

    try:
        broker = command_broker(host = args.host)
        broker.loop_forever()

        for thread in broker.threads_container:
            thread.join()

    except Exception as e:
        console.error(f"Exception : {e}")
    except KeyboardInterrupt as e:
        console.error(f"Keyboard Exception : {e}")
    
    exit(1)