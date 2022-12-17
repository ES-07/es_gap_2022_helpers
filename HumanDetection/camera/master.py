import fastapi
import os
#import responses
import pydantic
import kombu
import cv2
import datetime
import imutils
import json


from dotenv import load_dotenv
from pathlib import Path


dotenv_path = Path('.env')
load_dotenv(dotenv_path=dotenv_path)

RABBIT_MQ_URL = os.getenv('RABBIT_MQ_URL')
RABBIT_MQ_USERNAME = os.getenv('RABBIT_MQ_USERNAME')
RABBIT_MQ_PASSWORD = os.getenv('RABBIT_MQ_PASSWORD')
RABBIT_MQ_EXCHANGE_NAME = os.getenv('RABBIT_MQ_EXCHANGE_NAME')
RABBIT_MQ_QUEUE_NAME = os.getenv('RABBIT_MQ_QUEUE_NAME')


class VideoProducer:

    def __init__(self) -> None:
        self.rabbitUrl = RABBIT_MQ_URL
        self.username = RABBIT_MQ_USERNAME
        self.password = RABBIT_MQ_PASSWORD
        self.exchangeName = 'video-exchange'
        self.queueName = 'video-queue'
        self.frames_per_second_to_process = 2

    def createConnection(self):
        self.conn = kombu.Connection(
            f"amqp://{self.username}:{self.password}@{self.rabbitUrl}//", ssl=True)
        self.channel = self.conn.channel()
        self.exchange = kombu.Exchange(
            "video-exchange", type="direct", delivery_mode=1)
        self.kombu_producer = kombu.Producer(
            exchange=self.exchange, channel=self.channel, routing_key="video")
        self.queue = kombu.Queue(
            name=self.queueName, exchange=self.exchange, routing_key="video")
        self.queue.maybe_bind(self.conn)
        self.queue.declare()

    def processVideo(self, videoPath):
        video = cv2.VideoCapture(videoPath)
        check, frame = video.read()
        if not check:
            print("Video Not Found!")
            return

        # Compute the frame step
        video_fps = video.get(cv2.CAP_PROP_FPS)
        frame_step = video_fps/self.frames_per_second_to_process
        time_now = datetime.datetime.now()
        frame_count = 0
        frame_id = 0

        while video.isOpened():

            # check is True if reading was successful
            check, frame = video.read()

            if check:
                if frame_count % frame_step == 0:

                    # Resize frame
                    frame = imutils.resize(
                        frame,
                        width=min(800, frame.shape[1])
                    )

                    # Encode to JPEG
                    result, imgencode = cv2.imencode(
                        '.jpg',
                        frame,
                        [int(cv2.IMWRITE_JPEG_QUALITY), 90]
                    )

                    frame_seconds = frame_count/video_fps

                    # send a message
                    self.kombu_producer.publish(
                        body=imgencode.tobytes(),
                        content_type='image/jpeg',
                        content_encoding='binary',
                        headers={
                            "source": f"camera_1"
                        }
                    )

                    frame_id += 1

            else:
                self.kombu_producer.publish(
                    content_type='application/json',
                    body=json.dumps({"end": "True"})
                )
                break

            frame_count += 1


app = fastapi.FastAPI()


@app.get("/video")
def sendVideo(start: int, end: int):
    if (start < end):
        videoProducer = VideoProducer()
        videoProducer.createConnection()
        videoProducer.processVideo("samples/people-detection.mp4")

    else:
        raise fastapi.HTTPException(
            status_code=400, detail="start must be less than end")
