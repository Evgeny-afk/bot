#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import datetime
import urllib.request
import json
import socket
import yaml
import subprocess
from datetime import date, timedelta
from os.path import isfile, join
import glob
import psycopg2

#### Variables ####
server_ip = '127.0.0.1'
zabbix_metrics_log_file = '/tmp/zabbix_metrics_log_file.log'
zabbix_metrics_file = '/tmp/zabbix_metrics'
services_port_dict = {
    'app': 9011,
    'media': 9044,
    's3': 9000,
    'proxy': 443,
    'postgresql': 5432,
    # 'rabbitmq': 5672,
    # 'reddis': 6379,
    # 'test.py': 63342,
}
### CryptoPro ####
cryptopro_cert_expired_period = 30
cryptopro_port = 9060
#### GoRush #####
gorush_port = {
    'push': 8088,
    'voip': 8089
}
gorush_compose_path = '/opt/gostelemed/backend/gorush'
gorush_compose_file = 'docker-compose.yml'

#### DB ####
db_backup_dir = '/opt/db_backup'
storage_depth = 3 #days
db_backup_file_ext = 'dbbackup.tar.gz'

#### Service functions ####
def port_is_open() -> dict:
    open_ports ={}
    for app, port in services_port_dict.items():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)  # 2 Second Timeout
        result = sock.connect_ex((server_ip, port))
        open_ports[app] = result
    return open_ports

def define_server_role() -> str:
    open_ports = port_is_open()
    server_role = ''.join([app for app, port_status in open_ports.items() if bool(port_status) is False])
    return server_role

##### Metrics ###########
##### CryptoPro cert ####
def check_cryptopro_cert() -> list:
    src_url = 'http://{ip}:{port}/certificates'.format(ip='127.0.0.1', port=cryptopro_port)
    try:
        with urllib.request.urlopen(src_url) as response:
            cert_info = json.loads(response.read())
            status = cert_info.pop('status')
            if status == 'ok':
                cert_list = cert_info.pop('certificates')
                return cert_list
            else:
                write_to_log('Сервис КриптоПро недоступен')
    except:
        write_to_log('Сервис КриптоПро недоступен')

def check_cryptopro_cert_valid_time():
    metric_name = 'cryptoprocertexpire'
    result = ''
    metric_status = 0
    metric_value = 0
    current_time = int(datetime.datetime.now().timestamp())
    cryptopro_cert_expired_seconds = int(cryptopro_cert_expired_period) * 24 * 60 * 60
    try:
        cert_list = check_cryptopro_cert()
        for cert in cert_list:
            # if cert['hasPrivateKey']:
            cert_serial = cert['serialNumber']
            cert_valid_to = cert.pop('valid').pop('to')
            metric_msg = cert_valid_to.split(' ')[0]
            cert_valid_time = int(datetime.datetime.strptime(cert_valid_to, "%d.%m.%Y %H:%M:%S").timestamp())
            expire_time = cert_valid_time - current_time
            if expire_time/2 < cryptopro_cert_expired_seconds:
                metric_status = 2
                result = ('"{metric_name}": {{"status": "{metric_status}", "value": "{metric_value}", "msg": "{metric_msg}"}}'
                          .format(metric_name=metric_name, metric_status=metric_status, metric_value=metric_value, metric_msg=metric_msg))
                return result
            elif expire_time < cryptopro_cert_expired_seconds:
                metric_status = 1
                result = ('"{metric_name}": {{"status": "{metric_status}", "value": "{metric_value}", "msg": "{metric_msg}"}}'
                          .format(metric_name=metric_name, metric_status=metric_status, metric_value=metric_value, metric_msg=metric_msg))
                return result
            else:
                result = ('"{metric_name}": {{"status": "{metric_status}", "value": "{metric_value}", "msg": "{metric_msg}"}}'
                          .format(metric_name=metric_name, metric_status=metric_status, metric_value=metric_value, metric_msg=metric_msg))
    except:
        metric_status = 1
        metric_msg = 'Не удалось получить список КриптоПро сертификатов'
        result = ('"{metric_name}": {{"status": "{metric_status}", "value": "{metric_value}", "msg": "{metric_msg}"}}'
                  .format(metric_name=metric_name, metric_status=metric_status, metric_value=metric_value, metric_msg=metric_msg))
        write_to_log(metric_msg)
    return result

#### GoRush certs valid time ####
def fetch_gorush_services() -> list:
    gorush_compose = (os.path.join(gorush_compose_path, gorush_compose_file))
    with open(gorush_compose) as compose_file:
        gorush_services = yaml.safe_load(compose_file)['services']
        gorush_services = gorush_services.keys()
    return gorush_services

def gorush_ios_cert_expire():
    metric_name = 'gorushcertexpire'
    result = ''
    metric_status = 0
    metric_value = 0
    metric_msg = ''
    valid_sert = 'VALID'
    try:
        gorush_services = fetch_gorush_services()
        for service in gorush_services:
            docker_compose_comand = f'docker compose exec {service} /usr/local/bin/check-cert.sh'
            docker_compose_comand = docker_compose_comand.split(' ')
            result = subprocess.Popen(docker_compose_comand, cwd=gorush_compose_path, stdout=subprocess.PIPE)
            result = result.communicate()
            result = result[0].decode()
            if not valid_sert in result:
                metric_status = 1
                metric_msg = service
                result = ('"{metric_name}": {{"status": "{metric_status}", "value": "{metric_value}", "msg": "{metric_msg}"}}'
                          .format(metric_name=metric_name, metric_status=metric_status, metric_value=metric_value, metric_msg=metric_msg))
                return result
            else:
                result = ('"{metric_name}": {{"status": "{metric_status}", "value": "{metric_value}", "msg": "{metric_msg}"}}'
                          .format(metric_name=metric_name, metric_status=metric_status, metric_value=metric_value, metric_msg=metric_msg))
    except:
        metric_value = 1
        metric_msg = 'Не удалось получить список iOS сертификатов'
        result = ('"{metric_name}": {{"status": "{metric_status}", "value": "{metric_value}", "msg": "{metric_msg}"}}'
                  .format(metric_name=metric_name, metric_status=metric_status, metric_value=metric_value, metric_msg=metric_msg))
        write_to_log(metric_msg)
    return result

#### GoRush ios push_error ####
def gorush_ios_push_count():
    metric_name = 'gorushiospushcount'
    result = ''
    metric_status = 0
    metric_value = 0
    metric_msg = ''
    push_app = {
        'push': {
            'success': '',
            'error': ''
        },
        'voip': {
            'success': '',
            'error': ''
        }
    }
    for app, port in gorush_port.items():
        src_url = 'http://{ip}:{port}/api/stat/app'.format(ip='127.0.0.1', port=port)
        try:
            with urllib.request.urlopen(src_url) as response:
                ios_push_errors = json.loads(response.read())
                push_app[app]['success'] = ios_push_errors['ios']['push_success']
                push_app[app]['error'] = ios_push_errors['ios']['push_error']
        except:
            metric_value = 1
            metric_msg = 'Не удалось получить доступ к GoRush'
            result = ('"{metric_name}": {{"status": "{metric_status}", "value": "{metric_value}", "msg": "{metric_msg}"}}'
                      .format(metric_name=metric_name, metric_status=metric_status, metric_value=metric_value, metric_msg=metric_msg))
            write_to_log(metric_msg)
            return result
    result = ('"{metric_name}": {{"status": "{metric_status}", '
              '"pushsuccess": "{pushsuccess}", "pusherror": "{pusherror}", '
              '"voipsuccess": "{voipsuccess}", "voiperror": "{voiperror}", "msg": "{metric_msg}"}}'
              .format(metric_name=metric_name, metric_status=metric_status,
              pushsuccess=push_app['push']['success'],
              pusherror=push_app['push']['error'],
              voipsuccess=push_app['voip']['success'],
              voiperror=push_app['voip']['error'],
              metric_msg=metric_msg))
    return result

##### Check DB backup #####
def check_db_backup_exist():
    metric_name = 'dbbackup'
    result = ''
    metric_status = 0
    metric_value = 0
    metric_msg = ''
    days_list = [lambda i=i: (datetime.datetime.now() - timedelta(days=i)).strftime("%Y%m%d") for i in range(storage_depth)]
    for day in days_list:
        file_name = f'{day()}_*_{db_backup_file_ext}'
        file_name = join(db_backup_dir, file_name)
        file_list = glob.glob(file_name)
        if not file_list: ### backup missing
            metric_status = 1
            metric_msg = day()
            result = ('"{metric_name}": {{"status": "{metric_status}", "value": "{metric_value}", "msg": "{metric_msg}"}}'
                      .format(metric_name=metric_name, metric_status=metric_status, metric_value=metric_value, metric_msg=metric_msg))
            return result
        else:
            result = ('"{metric_name}": {{"status": "{metric_status}", "value": "{metric_value}", "msg": "{metric_msg}"}}'
                      .format(metric_name=metric_name, metric_status=metric_status, metric_value=metric_value, metric_msg=metric_msg))
    return result

##### SMS count #####
def sms_notification_count():
    metric_name = 'smscount'
    result = ''
    metric_status = 0
    metric_value = 0
    metric_msg = ''
    psql_request_sms_send = 'select count(id) from public.sms_message sm where status = \'SENT\' and created_at::date = current_date;'
    psql_request_sms_error = 'select count(id) from public.sms_message sm where status = \'ERROR\' and created_at::date = current_date;'
    try:
        conn = psycopg2.connect(dbname='notification_sender', user='postgres', password='', host='127.0.0.1')
        cursor = conn.cursor()
        cursor.execute(psql_request_sms_send)
        sms_send = cursor.fetchall()[0][0]
        cursor.execute(psql_request_sms_error)
        sms_error = cursor.fetchall()[0][0]
        cursor.close()
        conn.close()
        result = ('"{metric_name}": {{"status": "{metric_status}", "smssend": "{smssend}", "smserror": "{smserror}", "msg": "{metric_msg}"}}'
                  .format(metric_name=metric_name, metric_status=metric_status, smssend=sms_send, smserror=sms_error, metric_msg=metric_msg))
    except:
        metric_value = 1
        metric_msg = 'Не удалось получить доступ к базе даных'
        result = ('"{metric_name}": {{"status": "{metric_status}", "value": "{metric_value}", "msg": "{metric_msg}"}}'
                  .format(metric_name=metric_name, metric_status=metric_status, metric_value=metric_value, metric_msg=metric_msg))
        write_to_log(metric_msg)
    return result
##### Write to files ####
def write_to_log(msg):
    with open(zabbix_metrics_log_file, 'a') as log_file:
        _log_string = '[{date}] {msg} \n'.format(date=datetime.datetime.now(), msg=msg)
        log_file.write(_log_string)

def write_to_metrics(*msg):
    msg = ', '.join(msg)
    with open(zabbix_metrics_file, 'a') as metrics_file:
        metrics_string = f'{{"metrics": {{{msg}}}}}'
        metrics_file.write(metrics_string)

#### Main ####
def create_metrics():
    server_role =define_server_role()
    if server_role == 'app':
        cryptopro_cert = check_cryptopro_cert_valid_time()
        gorush_push_count = gorush_ios_push_count()
        gorush_cert = gorush_ios_cert_expire()
        write_to_metrics(cryptopro_cert, gorush_push_count, gorush_cert)
    if server_role == 'media':
        pass
    if server_role == 's3':
        pass
    if server_role == 'proxy':
        pass
    if server_role == 'db':
        check_backup = check_db_backup_exist()
        sms = sms_notification_count()
        write_to_metrics(check_backup, sms)

## Begin ####
write_to_log('Начало сбора метрик')
try:
    os.remove(zabbix_metrics_file)
except:
    print('Нет файла')
metrics = create_metrics()
write_to_log('Завершение сбора метрик')









##################################################################
# gorush_ios_cert_expire()



# metrics = {
#     'metric_name': {
#         'status': 1,
#         'value': '',
#         'msg': ''
#     }
# }


# fmba_backup_time{backup=\""$ndbs"_DB_Backups\"} `date +%s`\n

# write_to_metrisc('metric', 'msg', 'result')


# def write_to_log(msg):
#
#     with open(zabbix_metrics_log_file, 'a') as log_file:
#         _log_string = '[{date}] {msg} \n'.format(date=datetime.datetime.now(), msg=msg)
#         log_file.write(_log_string)
#
# __name__ == '__main__'
# if __name__ == '__main__':
#     if len(sys.argv) > 1:
#         globals()['choice_of_action'](sys.argv[1:])
#     else:
# #         write_to_log('Oтсутствуют аргументы')
# curl http://127.0.0.1:9060/certificates
# docker exec -i esiaauthservice-cryptopro-1 certmgr -list
#

# def gorush_ios_push_count():
#     metric_name = 'gorushpusherrors'
#     result = ''
#     metric_status = 0
#     metric_value = 0
#     metric_msg = ''
#     for app, port in gorush_port.items():
#         src_url = 'http://{ip}:{port}/api/stat/app'.format(ip='127.0.0.1', port=port)
#         try:
#             with urllib.request.urlopen(src_url) as response:
#                 ios_push_errors = json.loads(response.read())
#                 ios_push_errors = int(ios_push_errors['ios']['push_error'])
#                 ios_push_success = int(ios_push_errors['ios']['push_success'])
#                 if bool(ios_push_errors):
#                     metric_status = 1
#                     metric_value = ios_push_errors
#                     metric_msg = app
#                     result = ('"{metric_name}": {{"status": "{metric_status}", "value": "{metric_value}", "msg": "{metric_msg}"}}'
#                               .format(metric_name=metric_name, metric_status=metric_status, metric_value=metric_value, metric_msg=metric_msg))
#                     return result
#                 else:
#                     metric_value = ios_push_errors
#                     metric_msg = 'Ok'
#                     result = ('"{metric_name}": {{"status": "{metric_status}", "value": "{metric_value}", "msg": "{metric_msg}"}}'
#                               .format(metric_name=metric_name, metric_status=metric_status, metric_value=metric_value, metric_msg=metric_msg))
#         except:
#             metric_value = 1
#             metric_msg = 'Не удалось получить список сертификатов'
#             result = ('"{metric_name}": {{"status": "{metric_status}", "value": "{metric_value}", "msg": "{metric_msg}"}}'
#                       .format(metric_name=metric_name, metric_status=metric_status, metric_value=metric_value, metric_msg=metric_msg))
#             write_to_log('Не удалось получить список сертификатов')
#     return result

