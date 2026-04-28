FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY serial_pingbot.py .

ENV SERIAL_PORT=/dev/ttyACM0
ENV CHANNEL_IDX=1

CMD ["python", "-u", "serial_pingbot.py"]
