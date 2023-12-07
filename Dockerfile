FROM python:3.12-alpine
COPY ./requirements.txt /app/
RUN pip3 install -r /app/requirements.txt
COPY ./main.py /app/

ENTRYPOINT ["python3", "/app/main.py"]