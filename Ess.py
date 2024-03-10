import os
import time
import logging
import requests
import urllib3


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

        self.mqttClient.subscribe('/control/setWinterOnOff', self.__setWinterOnOff)

        self.__mirrorToMqtt()
        self.__keepAlive()

        self.scheduler.scheduleEach(self.__mirrorToMqtt, 60000)
        self.scheduler.scheduleEach(self.__keepAlive, 10000)

    def __setWinterOnOff(self, payload: str) -> None:

        startDate = '1231'
        endDate = '1231'

        match(payload):
            case 'On':
                startDate = '0101'
                self._writeData('user/setting/batt', {'startdate': startDate, 'stopDate': endDate})
            case 'Off':
                startDate = '1231'
                self._writeData('user/setting/batt', {'startdate': startDate, 'stopDate': endDate})
            case _:
                pass

    def __readAuthData(self) -> dict:

        api_url = f'https://{self.ip}/v1/login'
        body = {"password": self.passWd}

        response = requests.put(api_url, json=body, headers={'Content-Type': 'application/json'}, verify=False, timeout=10)
        responseObj = response.json()

        return responseObj

    def __readData(self, endpoint: str) -> dict:
        responseObj = {}

        try:
            auth = self.__readAuthData()
            if auth['status'] == 'success':

                api_url = f'https://{self.ip}/v1/{endpoint}'
                body = {"auth_key": auth['auth_key']}

                response = requests.post(api_url, json=body, headers={'Content-Type': 'application/json'}, verify=False, timeout=10)
                responseObj = response.json()
        except BaseException:
            logging.exception('')

        return responseObj

    def _writeData(self, endpoint: str, body: object) -> dict:
        responseObj = {}

        try:
            auth = self.__readAuthData()
            if auth['status'] == 'success':

                api_url = f'https://{self.ip}/v1/{endpoint}'
                body["auth_key"] = auth['auth_key']

                response = requests.put(api_url, json=body, headers={'Content-Type': 'application/json'}, verify=False, timeout=10)
                responseObj = response.json()
        except BaseException:
            logging.exception('')

        return responseObj

    def __mirrorToMqtt(self) -> None:

        valuesForSending = []

        essInfoHome = self.__readData('user/essinfo/home')
        essInfoHomeCorrected = self.__correctPowerDirection(essInfoHome)

        if essInfoHomeCorrected:
            valuesForSending = valuesForSending + DictUtil.flatDict(essInfoHomeCorrected, "essinfo_home")
            valuesForSending = valuesForSending + DictUtil.flatDict(self.__readData('user/setting/systeminfo'), "setting_systeminfo")
            valuesForSending = valuesForSending + DictUtil.flatDict(self.__readData('user/setting/batt'), "setting_batt")
            valuesForSending = valuesForSending + DictUtil.flatDict(self.__readData('user/essinfo/common'), "essinfo_common")
            valuesForSending = valuesForSending + DictUtil.flatDict(self.__readData('user/setting/network'), "setting_network")

            for value in valuesForSending:
                self.mqttClient.publishOnChange(value[0], value[1])

    def __correctPowerDirection(self, essInfoHome: dict) -> dict:

        if 'direction' in essInfoHome and 'statistics' in essInfoHome:

            # is_direct_consuming_ = True if '1' == essInfoHome['direction']['is_direct_consuming_'] else False
            is_battery_charging_ = True if '1' == essInfoHome['direction']['is_battery_charging_'] else False
            # is_battery_discharging_ = True if '1' == essInfoHome['direction']['is_battery_discharging_'] else False
            is_grid_selling_ = True if '1' == essInfoHome['direction']['is_grid_selling_'] else False
            # is_grid_buying_ = True if '1' == essInfoHome['direction']['is_grid_buying_'] else False
            is_charging_from_grid_ = True if '1' == essInfoHome['direction']['is_charging_from_grid_'] else False
            # is_discharging_to_grid_ = True if '1' == essInfoHome['direction']['is_discharging_to_grid_'] else False

            essInfoHome['statistics']['pcs_pv_total_power_org'] = essInfoHome['statistics']['pcs_pv_total_power']
            essInfoHome['statistics']['batconv_power_org'] = essInfoHome['statistics']['batconv_power']
            essInfoHome['statistics']['load_power_org'] = essInfoHome['statistics']['load_power']
            essInfoHome['statistics']['grid_power_org'] = essInfoHome['statistics']['grid_power']

            if is_battery_charging_ or is_charging_from_grid_:
                essInfoHome['statistics']['batconv_power'] = str(float(essInfoHome['statistics']['batconv_power']) * (-1))

            essInfoHome['statistics']['load_power'] = str(float(essInfoHome['statistics']['load_power']) * (-1))

            if is_grid_selling_:
                essInfoHome['statistics']['grid_power'] = str(float(essInfoHome['statistics']['grid_power']) * (-1))

            return essInfoHome
        else:
            return None

    def __keepAlive(self) -> None:
        self.mqttClient.publishIndependentTopic('/house/agents/Ess2Mqtt/heartbeat', DateTimeUtilities.getCurrentDateString())
        self.mqttClient.publishIndependentTopic('/house/agents/Ess2Mqtt/subscriptions', JsonUtil.obj2Json(self.mqttClient.getSubscriptionCatalog()))


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('Ess').setLevel(logging.DEBUG)

    module = Module()
    module.setup()

    logging.getLogger('Ess').addHandler(MQTTHandler(module.getMqttClient(), '/house/agents/Ess2Mqtt/log'))

    Ess(PASSWD, IP, module).setup()

    print("Ess2Mqtt is running")

    while (True):
        module.loop()
        time.sleep(0.25)


if __name__ == '__main__':
    main()
