
import kombu
import datetime
import json

class SendFrames:

    kombu_connection = None
    kombu_exchange = None
    kombu_channel = None
    kombu_producer = None
    kombu_queue = None

    def __init__(self)->None:
        pass
        


    def attach_to_message_broker(self, broker_url, broker_username,
                                 broker_password, exchange_name, queue_name):
                                 
        connection_string = f"amqp://{broker_username}:{broker_password}" \
            f"@{broker_url}/"

        # Kombu Connection
        self.kombu_connection = kombu.Connection(connection_string)
        self.kombu_channel = self.kombu_connection.channel()

        # Kombu Exchange
        self.kombu_exchange = kombu.Exchange(
            name=self.kombu_exchange,
            type="direct"
        )

        # Kombu Producer
        self.kombu_producer = kombu.Producer(
            exchange=self.kombu_exchange,
            channel=self.kombu_channel,
            routing_key=queue_name
        )


    def send_notification(self, timestamp, camera_id, frame_id):
        self.kombu_producer.publish(
            body=json.dumps("{timestamp: "+str(timestamp)+
            ", camera_id: "+str(camera_id)+
            ", frame_id: "+str(frame_id)+"}"
            ),
        )


if __name__ == "__main__":
    RABBIT_MQ_URL = "localhost:5672"
    RABBIT_MQ_USERNAME = "myuser"
    RABBIT_MQ_PASSWORD = "mypassword"
    RABBIT_MQ_EXCHANGE_NAME = "human-detection-exchange"
    RABBIT_MQ_QUEUE_NAME = "human-detection-queue"


    send_frames = SendFrames()
    
    send_frames.attach_to_message_broker(
        RABBIT_MQ_URL, 
        RABBIT_MQ_USERNAME, 
        RABBIT_MQ_PASSWORD, 
        RABBIT_MQ_EXCHANGE_NAME, 
        RABBIT_MQ_QUEUE_NAME
        )

    send_frames.send_notification()