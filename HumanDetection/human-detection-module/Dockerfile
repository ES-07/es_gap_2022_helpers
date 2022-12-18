FROM python:3.9-slim


WORKDIR /human-detection-module

RUN apt-get update
RUN apt-get install ffmpeg libsm6 libxext6  -y

COPY requirements.txt .

RUN pip3 install --no-cache-dir --upgrade -r requirements.txt

COPY . .

CMD [ "python","-u", "main.py" ]