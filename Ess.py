import logging
import requests
import time
import urllib3
import os


import paho.mqtt.client as pahoMqtt
from PythonLib.Mqtt import Mqtt
from PythonLib.Scheduler import Scheduler
from PythonLib.DictUtil import DictUtil

logger = logging.getLogger('Ess')
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

IP = "10.10.40.11"
PASSWD = os.environ.get("PASSWDESS")


class Ess:
    def __init__(self, passWd: str, ip: str, mqttClient: Mqtt, scheduler: Scheduler) -> None:
        self.passWd = passWd
        self.ip = ip
        self.mqttClient = mqttClient
        self.scheduler = scheduler

    def setup(self) -> None:
        self.scheduler.scheduleEach(self.mqttClient.loop, 500)
        self.scheduler.scheduleEach(self.loop, 1000)
        self.scheduler.scheduleEach(self.mirrorToMqtt, 5000)

    def readAuthData(self) -> dict:
        api_url = f'https://{self.ip}/v1/login'
        body = {"password": self.passWd}

        response = requests.put(api_url, json=body, headers={'Content-Type': 'application/json'}, verify=False)
        return response.json()

    def readData(self, auth: dict, endpoint: str) -> dict:
        api_url = f'https://{self.ip}/v1/{endpoint}'
        body = {"auth_key": auth['auth_key']}

        response = requests.post(api_url, json=body, headers={'Content-Type': 'application/json'}, verify=False)
        return response.json()

    def mirrorToMqtt(self) -> None:

        auth = self.readAuthData()

        if auth['status'] == 'success':

            valuesForSending = []

            valuesForSending = valuesForSending + DictUtil.flatDict(self.readData(auth, 'user/essinfo/home'), "essinfo_home")
            valuesForSending = valuesForSending + DictUtil.flatDict(self.readData(auth, 'user/setting/systeminfo'), "setting_systeminfo")
            valuesForSending = valuesForSending + DictUtil.flatDict(self.readData(auth, 'user/setting/batt'), "setting_batt")
            valuesForSending = valuesForSending + DictUtil.flatDict(self.readData(auth, 'user/essinfo/common'), "essinfo_common")
            valuesForSending = valuesForSending + DictUtil.flatDict(self.readData(auth, 'user/setting/network'), "setting_network")

            for value in valuesForSending:
                self.mqttClient.publishOnChange(value[0], value[1])


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('Ess').setLevel(logging.DEBUG)

    mqttClient = Mqtt("koserver.iot", "/house/basement/ess", pahoMqtt.Client("Ess"))
    scheduler = Scheduler()

    ess = Ess(PASSWD, IP, mqttClient, scheduler)
    ess.setup()

    while (True):
        scheduler.loop()
        time.sleep(0.25)


if __name__ == '__main__':
    main()
