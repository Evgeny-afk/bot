FROM python:3.12-alpine
COPY ./main.py /app/
COPY ./requirements.txt /app/
RUN pip3 install -r /app/requirements.txt

ENTRYPOINT ["python3", "/app/main.py"]