# @Author: Rafael Direito
# @Date:   2022-10-06 11:31:00 (WEST)
# @Email:  rdireito@av.it.pt
# @Copyright: Insituto de Telecomunicações - Aveiro, Aveiro, Portugal
# @Last Modified by:   Rafael Direito
# @Last Modified time: 2022-10-07 11:42:57

import numpy as np
import cv2
import sys
import kombu
from kombu.mixins import ConsumerMixin
import datetime
import os
import glob
import redis
import requests
import time
import send_frames
import datetime

from dotenv import load_dotenv
from pathlib import Path


dotenv_path = Path('../.env')
load_dotenv(dotenv_path=dotenv_path)

RABBIT_MQ_URL = os.getenv('RABBIT_MQ_URL')
RABBIT_MQ_USERNAME = os.getenv('RABBIT_MQ_USERNAME')
RABBIT_MQ_PASSWORD = os.getenv('RABBIT_MQ_PASSWORD')
RABBIT_MQ_EXCHANGE_NAME = "human-detection-exchange"
RABBIT_MQ_QUEUE_NAME = "cameras-gateway"


# Comment these lines to use AWS Broker
RABBIT_MQ_URL = "localhost:5672"
RABBIT_MQ_USERNAME = "myuser"
RABBIT_MQ_PASSWORD = "mypassword"

BASE_URL = "http://localhost:8000"

# Kombu Message Consuming Human_Detection_Worker
class Human_Detection_Worker(ConsumerMixin):


    def __init__(self, connection, queues, database, output_dir):
        self.connection = connection
        self.queues = queues
        self.database = database
        self.output_dir = output_dir
        self.HOGCV = cv2.HOGDescriptor()
        self.HOGCV.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        self.b = True
        
        
        self.messageQueueIntrusionApi = send_frames.SendFrames()
        self.messageQueueIntrusionApi.attach_to_message_broker(
            RABBIT_MQ_URL, 
            RABBIT_MQ_USERNAME, 
            RABBIT_MQ_PASSWORD, 
            RABBIT_MQ_EXCHANGE_NAME, 
            RABBIT_MQ_QUEUE_NAME
        )




    def detect_number_of_humans(self, frame):
        bounding_box_cordinates, _ = self.HOGCV.detectMultiScale(
            frame,
            winStride=(4, 4),
            padding=(8, 8),
            scale=1.03
        )
        return len(bounding_box_cordinates)


    def get_consumers(self, Consumer, channel):
        return [
            Consumer(
                queues=self.queues,
                callbacks=[self.on_message],
                accept=['image/jpeg']
                )
            ]


    def on_message(self, body, message):
        # Get message headers' information
        msg_source = message.headers["source"]
        frame_timestamp = message.headers["timestamp"]
        frame_count = message.headers["frame_count"]
        frame_id = message.headers["frame_id"]

        if frame_count==0:
            timestamp = int(time.mktime(datetime.datetime.strptime(frame_timestamp,"%Y-%m-%d %H:%M:%S.%f").timetuple()))
            self.firstIntrusion = timestamp

        # Debug
        print(f"I received the frame number {frame_count} from {msg_source}" +
              f", with the timestamp {frame_timestamp}.")
        print("I'm processing the frame...")

        ts_processing_start = datetime.datetime.now()
        # Process the Frame
        # Get the original  byte array size
        size = sys.getsizeof(body) - 33
        # Jpeg-encoded byte array into numpy array
        np_array = np.frombuffer(body, dtype=np.uint8)
        np_array = np_array.reshape((size, 1))
        # Decode jpeg-encoded numpy array
        image = cv2.imdecode(np_array, 1)
        num_humans = self.detect_number_of_humans(image)

        # Compute Processing Time
        ts_processing_end = datetime.datetime.now()
        processing_duration = ts_processing_end - ts_processing_start
        processing_duration_ms = processing_duration.total_seconds() * 1000

        print(f"Frame {frame_count} has {num_humans} human(s), and was " +
              f"processed in {processing_duration_ms} ms.")

        # Save to Database
        

        self.create_database_entry(
            camera_id=msg_source,
            frame_id=frame_id,
            num_humans=num_humans,
            ts=frame_timestamp
        )




        # Do we need to raise an alarm?
        alarm_raised = self.alarm_if_needed(
            camera_id=msg_source,
            frame_id=frame_id,
        )

        if alarm_raised:
            ts_str = frame_timestamp.replace(":", "-").replace(" ", "_")
            filename = f"intruder_camera_id_{msg_source}" \
                f"_frame_id_{frame_id}" \
                f"_frame_timestamp_{ts_str}" \
                ".jpeg"
            output_image_path = os.path.join(self.output_dir, filename)
            cv2.imwrite(output_image_path, image)
            
        print("\n")

        # Remove Message From Queue
        message.ack()


    def create_database_entry(self, camera_id, frame_id, num_humans, ts):
        # Create two entries in db. One for the camera_id and frame id with value num humans
        # the other one is for the camera id and frame id with value timestamp
        num_humans_key = f"camera_{camera_id}_frame_{frame_id}_n_humans"
        timestamp_key = f"camera_{camera_id}_frame_{frame_id}_timestamp"
        self.database.set(num_humans_key,num_humans)
        self.database.set(timestamp_key,ts)


    def alarm_if_needed(self, camera_id, frame_id):
        n_human_key = f"camera_{camera_id}_frame_{frame_id}_n_humans"
        prev1_n_human_key = f"camera_{camera_id}_frame_{frame_id-1}_n_humans"
        prev2_n_human_key = f"camera_{camera_id}_frame_{frame_id-2}_n_humans"

        prev1_frame_n_humans = int(self.database.get(prev1_n_human_key)) if self.database.exists(prev1_n_human_key) else 0
        curr_frame_n_humans = int(self.database.get(n_human_key)) if self.database.exists(n_human_key) else 0
        prev2_frame_n_humans = int(self.database.get(prev2_n_human_key)) if self.database.exists(prev2_n_human_key) else 0

        if prev1_frame_n_humans + curr_frame_n_humans + prev2_frame_n_humans >= 3 and self.b:
            # aqui ele vai comunicar com a api de intrusão
            self.b=False
            total_n_humans = prev1_frame_n_humans + curr_frame_n_humans + prev2_frame_n_humans
            timestamp_key = f"camera_{camera_id}_frame_{frame_id}_timestamp"
            timestamp = self.database.get(timestamp_key)   

            timestamp = int(time.mktime(datetime.datetime.strptime(timestamp,"%Y-%m-%d %H:%M:%S.%f").timetuple()))
            #if timestamp > 3*60 + self.lastIntrusion:
                #self.lastIntrusion = timestamp
                
            
            # send to intrusion api
            response = requests.post(BASE_URL+'/intrusions', json={'timestamp': str(timestamp), 'building_id': 1, 'device_id': int(camera_id.split("_")[1])})
            print("--------> " , response)
        
            print(f"[!!!] INTRUDER DETECTED AT TIMESTAMP {timestamp}[!!!]")
            return True
        return False


class Human_Detection_Module:

    def __init__(self, output_dir):
        self.database = self.init_database()
        self.output_dir = output_dir
        self.__bootstrap_output_directory()

    def init_database(self):
        return redis.Redis(host='localhost',port=6379, charset="utf-8", decode_responses=True)

    def __bootstrap_output_directory(self):
        if os.path.isdir(self.output_dir):
            files = os.listdir(self.output_dir)
            for f in files:
                os.remove(os.path.join(self.output_dir, f))
        else:
            os.mkdir(self.output_dir)

    def start_processing(self, broker_url, broker_username,
                         broker_password, exchange_name, queue_name):

        # Create Connection String
        connection_string = f"amqp://{broker_username}:{broker_password}" \
            f"@{broker_url}/"

        # Kombu Exchange
        self.kombu_exchange = kombu.Exchange(
            name=exchange_name,
            type="direct",
        )

        # Kombu Queues
        self.kombu_queues = [
            kombu.Queue(
                name=queue_name,
                exchange=self.kombu_exchange
            )
        ]

        # Kombu Connection
        self.kombu_connection = kombu.Connection(
            connection_string,
            heartbeat=4
        )

        # Start Human Detection Workers

        """
        Idea to turn the HDM scalable.
        When the frame rate of the received messages increases, then create more workers to process the frames.
        Initially, when this value is low one worker can process all the information
        However, when this is not the case, each worker should update its HDM results to the database and the 3rd one should check if there are humans in the last frames

        Difficulties:
        How each of them connects to the database (redis)
        How to dynamically create/destroy workers
        Which worker is the responsible for human intrusion detection?




        check_if_need_workers()

        [Human_Detection_Worker(
            connection=self.kombu_connection,
            queues=self.kombu_queues,
            database=self.database,
            output_dir=self.output_dir
        )
        for i in range(num_of_needed_workers()
        )]

        """


        self.human_detection_worker = Human_Detection_Worker(
            connection=self.kombu_connection,
            queues=self.kombu_queues,
            database=self.database,
            output_dir=self.output_dir
        )
        self.human_detection_worker.run()
