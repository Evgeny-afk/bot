#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import datetime
import urllib.request
import json
import socket

#### Variables ####
zabbix_metrics_log_file = '/tmp/zabbix_metrics_log_file.log'
zabbix_metrics_file = '/tmp/zabbix_metrics'
cryptopro_cert_expired_period = 30
cryptopro_port = 9060
gorush_port = {
    'push': 8088,
    'voip': 8081
}

server_ip = '127.0.0.1'
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
######################

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
######################

##### Metrics ####
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
            if expire_time < cryptopro_cert_expired_seconds:
                metric_status = 1
                result = '"{metric_name}": {{"status": "{metric_status}", "value": "{metric_value}", "msg": "{metric_msg}"}}'.format(metric_name=metric_name, metric_status=metric_status, metric_value=metric_value, metric_msg=metric_msg)
                return result
            else:
                result = '"{metric_name}": {{"status": "{metric_status}", "value": "{metric_value}", "msg": "{metric_msg}"}}'.format(metric_name=metric_name, metric_status=metric_status, metric_value=metric_value, metric_msg=metric_msg)
    except:
        metric_status = 1
        metric_msg = 'Не удалось получить список сертификатов'
        result = '"{metric_name}": {{"status": "{metric_status}", "value": "{metric_value}", "msg": "{metric_msg}"}}'.format(metric_name=metric_name, metric_status=metric_status, metric_value=metric_value, metric_msg=metric_msg)
    return result
######################

#### GoRush certs valid time ####

######################

#### GoRush ios push_error ####
def gorush_ios_push_errors():
    metric_name = 'gorushpusherrors'
    result = ''
    metric_status = 0
    metric_value = 0
    metric_msg = ''
    for app, port in gorush_port.items():
        src_url = 'http://{ip}:{port}/api/stat/app'.format(ip='127.0.0.1', port=port)
        try:
            with urllib.request.urlopen(src_url) as response:
                ios_push_errors = json.loads(response.read())
                ios_push_errors = int(ios_push_errors['ios']['push_error'])
                if not ios_push_errors:
                    metric_value = ios_push_errors
                    metric_msg = app
                    result = '"{metric_name}": {{"status": "{metric_status}", "value": "{metric_value}", "msg": "{metric_msg}"}}'.format(metric_name=metric_name, metric_status=metric_status, metric_value=metric_value, metric_msg=metric_msg)
                else:
                    metric_value = ios_push_errors
                    metric_msg = 'Ok'
                    result = '"{metric_name}": {{"status": "{metric_status}", "value": "{metric_value}", "msg": "{metric_msg}"}}'.format(metric_name=metric_name, metric_status=metric_status, metric_value=metric_value, metric_msg=metric_msg)
        except:
            metric_value = 1
            metric_msg = 'Не удалось получить список сертификатов'
            result = '"{metric_name}": {{"status": "{metric_status}", "value": "{metric_value}", "msg": "{metric_msg}"}}'.format(metric_name=metric_name, metric_status=metric_status, metric_value=metric_value, metric_msg=metric_msg)
            write_to_log('Не удалось получить список сертификатов')
    return result
###################### ####

######################

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
######################

#### Main ####
def create_metrics():
    server_role =define_server_role()
    if server_role == 'app':
        cryptopro_cert = check_cryptopro_cert_valid_time()
        gorus_err = gorush_ios_push_errors()
        write_to_metrics(cryptopro_cert, gorus_err)
    if server_role == 'media':
        pass
    if server_role == 's3':
        pass
    if server_role == 'proxy':
        pass
    if server_role == 'db':
        pass

### Begin ####
write_to_log('Начало сбора метрик')
try:
    os.remove(zabbix_metrics_file)
except:
    print('Нет файла')
metrics = create_metrics()
write_to_log('Завершение сбора метрик')





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
