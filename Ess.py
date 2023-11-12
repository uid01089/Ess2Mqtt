import logging
import requests
import time
import urllib3
import os


import paho.mqtt.client as pahoMqtt
from PythonLib.JsonUtil import JsonUtil
from PythonLib.Mqtt import MQTTHandler, Mqtt
from PythonLib.Scheduler import Scheduler
from PythonLib.DictUtil import DictUtil
from PythonLib.DateUtil import DateTimeUtilities

logger = logging.getLogger('Ess')
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

IP = "10.10.40.11"
PASSWD = os.environ.get("PASSWDESS")


class Module:
    def __init__(self) -> None:
        self.scheduler = Scheduler()
        self.mqttClient = Mqtt("koserver.iot", "/house/basement/ess", pahoMqtt.Client("Ess"))

    def getScheduler(self) -> Scheduler:
        return self.scheduler

    def getMqttClient(self) -> Mqtt:
        return self.mqttClient

    def setup(self) -> None:
        self.scheduler.scheduleEach(self.mqttClient.loop, 500)

    def loop(self) -> None:
        self.scheduler.loop()


class Ess:
    def __init__(self, passWd: str, ip: str, module: Module) -> None:
        self.passWd = passWd
        self.ip = ip
        self.mqttClient = module.getMqttClient()
        self.scheduler = module.getScheduler()

    def setup(self) -> None:

        self.scheduler.scheduleEach(self.mirrorToMqtt, 30000)
        self.scheduler.scheduleEach(self.__keepAlive, 10000)

    def readAuthData(self) -> dict:

        api_url = f'https://{self.ip}/v1/login'
        body = {"password": self.passWd}

        response = requests.put(api_url, json=body, headers={'Content-Type': 'application/json'}, verify=False, timeout=10)
        responseObj = response.json()

        return responseObj

    def readData(self, endpoint: str) -> dict:
        responseObj = {}

        try:
            auth = self.readAuthData()
            if auth['status'] == 'success':

                api_url = f'https://{self.ip}/v1/{endpoint}'
                body = {"auth_key": auth['auth_key']}

                response = requests.post(api_url, json=body, headers={'Content-Type': 'application/json'}, verify=False, timeout=10)
                responseObj = response.json()
        except BaseException:
            logging.exception('')

        return responseObj

    def mirrorToMqtt(self) -> None:

        valuesForSending = []

        valuesForSending = valuesForSending + DictUtil.flatDict(self.readData('user/essinfo/home'), "essinfo_home")
        valuesForSending = valuesForSending + DictUtil.flatDict(self.readData('user/setting/systeminfo'), "setting_systeminfo")
        valuesForSending = valuesForSending + DictUtil.flatDict(self.readData('user/setting/batt'), "setting_batt")
        valuesForSending = valuesForSending + DictUtil.flatDict(self.readData('user/essinfo/common'), "essinfo_common")
        valuesForSending = valuesForSending + DictUtil.flatDict(self.readData('user/setting/network'), "setting_network")

        for value in valuesForSending:
            self.mqttClient.publishOnChange(value[0], value[1])

    def __keepAlive(self) -> None:
        self.mqttClient.publishIndependentTopic('/house/agents/Ess2Mqtt/heartbeat', DateTimeUtilities.getCurrentDateString())
        self.mqttClient.publishIndependentTopic('/house/agents/Ess2Mqtt/subscriptions', JsonUtil.obj2Json(self.mqttClient.getSubscriptionCatalog()))


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('Ess').setLevel(logging.DEBUG)

    module = Module()

    logging.getLogger('Ess').addHandler(MQTTHandler(module.getMqttClient(), '/house/agents/Ess2Mqtt/log'))

    Ess(PASSWD, IP, module).setup()

    print("Ess2Mqtt is running")

    while (True):
        module.loop()
        time.sleep(0.25)


if __name__ == '__main__':
    main()
