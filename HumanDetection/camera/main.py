# @Author: Rafael Direito
# @Date:   2022-10-06 10:54:18 (WEST)
# @Email:  rdireito@av.it.pt
# @Copyright: Insituto de Telecomunicações - Aveiro, Aveiro, Portugal
# @Last Modified by:   Rafael Direito
# @Last Modified time: 2022-10-06 11:19:15

import os
import requests
import random
from dotenv import load_dotenv
from pathlib import Path

from camera import Camera


# Load environment variables
dotenv_path = Path('../.env')
load_dotenv(dotenv_path=dotenv_path)


def get_random_device_id(api_url):
    response = requests.get(f"{api_url}/devices")
    if response.status_code == 200:
        devices = response.json()
        return devices[random.randint(0, len(devices) - 1)]['id']
    return None

SITES_MANAGEMENT_API_URL = os.getenv('SITES_MANAGEMENT_API_URL')
# CAMERA VARIABLES
CAMERA_ID = get_random_device_id(SITES_MANAGEMENT_API_URL)
NUM_FRAMES_PER_SECOND_TO_PROCESS = 2


RABBIT_MQ_URL = os.getenv('RABBIT_MQ_URL')
RABBIT_MQ_USERNAME = os.getenv('RABBIT_MQ_USERNAME')
RABBIT_MQ_PASSWORD = os.getenv('RABBIT_MQ_PASSWORD')
RABBIT_MQ_EXCHANGE_NAME = os.getenv('RABBIT_MQ_EXCHANGE_NAME')
RABBIT_MQ_QUEUE_NAME = os.getenv('RABBIT_MQ_QUEUE_NAME')


camera = Camera(
    camera_id=CAMERA_ID,
    frames_per_second_to_process=NUM_FRAMES_PER_SECOND_TO_PROCESS
)

camera.attach_to_message_broker(
    broker_url=RABBIT_MQ_URL,
    broker_username=RABBIT_MQ_USERNAME,
    broker_password=RABBIT_MQ_PASSWORD,
    exchange_name=RABBIT_MQ_EXCHANGE_NAME,
    queue_name=RABBIT_MQ_QUEUE_NAME
)

camera.transmit_video("samples/people-detection.mp4")

print("End of video transmission")
