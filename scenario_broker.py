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


"""
# 가상환경 내 Python 경로
python_executable = sys.executable

# 실행할 Python 프로그램과 인자
script_path = "/path/to/other_program.py"
args = ["arg1", "arg2"]

# 독립적인 프로세스로 실행
process = subprocess.Popen([python_executable, script_path] + args)

# 프로세스가 종료될 때까지 기다리려면 .wait() 사용
# process.wait()
"""

"""
import os

# 현재 환경 변수를 복사
env = os.environ.copy()
env["MY_VAR"] = "some_value"

process = subprocess.Popen(
    [python_executable, script_path],
    env=envqudgns

)
"""

TOPIC = "flame/avsim/broker/process_run"




def on_mqtt_connect(self, client, userdata, flags, reason_code, properties):
    """ mqtt connection """
    if reason_code==0:
        for topic in self.message_api.keys():
            self.mq_client.subscribe(topic, 0)
        print("Connected to broker for DualControl")
    else:
        print("Connection Failed")

def on_mqtt_message(self, client, userdata, msg):
    """on message received """
    mapi = str(msg.topic)
    try:
        if mapi in self.message_api.keys():
            payload = json.loads(msg.payload)
            self.message_api[mapi](payload)
            
    except json.JSONDecodeError as e:
        print("Message API parse error occurred!")

def on_mqtt_disconnect(self, client, userdata, reason_code):
    print("disconnected to broker for DUalControl")

def on_process_run(self):
    """process run command with arguments """
    pass

# message api
message_api = {
                "flame/avsim/broker/process_run": on_process_run
            }


if __name__=="__main__":
    console = ConsoleLogger.get_logger()

    mq_client = mqtt.Client(client_id="avsim_monitor", transport='tcp', protocol=mqtt.MQTTv311, clean_session=True)
    mq_client.on_connect = on_mqtt_connect
    mq_client.on_message = on_mqtt_message
    mq_client.on_disconnect = on_mqtt_disconnect

    try:
        mq_client.connect(host="192.168.0.30", port=1883, keepalive=60)
    except Exception as e:
        print(f"Could not connect to Broker : {e}")
        exit(1)

    mq_client.loop_forever() # waiting for ever