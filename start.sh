#! /bin/bash
cd /home/pi/homeautomation/Ess2Mqtt
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 Ess.py > /home/pi/homeautomation/Ess2Mqtt/Ess.log
