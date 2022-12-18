FROM python:3.9-slim

WORKDIR /camera


ARG RABBIT_MQ_USERNAME=$RABBIT_MQ_USERNAME
ARG RABBIT_MQ_PASSWORD=$RABBIT_MQ_PASSWORD
ARG RABBIT_MQ_URL=$RABBIT_MQ_URL
ARG RABBIT_MQ_EXCHANGE_NAME=$RABBIT_MQ_EXCHANGE_NAME
ARG RABBIT_MQ_QUEUE_NAME=$RABBIT_MQ_QUEUE_NAME


RUN apt-get update
RUN apt-get install ffmpeg libsm6 libxext6  -y

COPY requirements.txt .

RUN pip3 install --no-cache-dir --upgrade -r requirements.txt

COPY . .

CMD ["uvicorn", "master:app", "--host", "0.0.0.0", "--port", "8000"]

EXPOSE 8000