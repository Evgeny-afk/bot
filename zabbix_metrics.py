#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import datetime
import urllib.request
import json
import socket

#### Variables ####
zabbix_metrics_log_file = '/tmp/zabbix_metrics_log_file.log'
zabbix_metrics_file = '/tmp/zabbix_metrics_file'
cryptopro_cert_expired_period = 30
cryptopro_port = 9060
server_ip = '127.0.0.1'
services_port_dict = {
    'app': 9011,
    'media': 9044,
    's3': 9000,
    'proxy': 443,
    'postgresql': 5432,
    # 'rabbitmq': 5672,
    # 'reddis': 6379,
    # 'test': 63342,
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
def check_cryptopro_cert():
    metric_name = 'cryptopro_cert_expire'
    src_url = 'http://{ip}:{port}/certificates'.format(ip='127.0.0.1', port=cryptopro_port)
    try:
        with urllib.request.urlopen(src_url) as response:
            cert_info = json.loads(response.read())
            status = cert_info.pop('status')
            if status == 'ok':
                cert_list = cert_info.pop('certificates')
                check_cryptopro_cert_valid_time(cert_list)
            else:
                write_to_metrics(metric_name, 1)
                write_to_log('Сервис КриптоПро недоступен')
    except:
        write_to_metrics(metric_name, 1)
        write_to_log('Сервис КриптоПро недоступен')

def check_cryptopro_cert_valid_time(cert_list):
    metric_name = 'cryptopro_cert_expire'
    current_time = int(datetime.datetime.now().timestamp())
    cryptopro_cert_expired_seconds = int(cryptopro_cert_expired_period) * 24 * 60 * 60
    for cert in cert_list:
        if cert['hasPrivateKey']:
            cert_serial = cert['serialNumber']
            cert_valid_to = cert.pop('valid').pop('to')
            cert_valid_time = int(datetime.datetime.strptime(cert_valid_to, "%d.%m.%Y %H:%M:%S").timestamp())
            expire_time = cert_valid_time - current_time
            if expire_time < cryptopro_cert_expired_seconds:
                write_to_metrics(metric_name, 1, cert_serial)
            else:
                write_to_metrics(metric_name, 0, cert_serial)
######################

##### Write to files ####
def write_to_log(msg):
    with open(zabbix_metrics_log_file, 'a') as log_file:
        _log_string = '[{date}] {msg} \n'.format(date=datetime.datetime.now(), msg=msg)
        log_file.write(_log_string)

def write_to_metrics(metric, result, *msg):
    with open(zabbix_metrics_file, 'a') as metrics_file:
        _metrics_string = '{metric} {result} \n'.format(metric=metric, msg=msg, result=result )
        # _metrics_string = '{metric}{{{msg}}} {result} \n'.format(metric=metric, msg=msg, result=result )
        metrics_file.write(_metrics_string)
######################

#### Main ####
def create_metrics():
    server_role =define_server_role()
    if server_role == 'app':
        check_cryptopro_cert()
    if server_role == 'media':
        pass
    if server_role == 's3':
        pass
    if server_role == 'proxy':
        pass
    if server_role == 'db':
        pass

#### Begin ####
write_to_log('Начало сбора метрик')
try:
    os.remove(zabbix_metrics_file)
except:
    print('Нет файла')
metrics = create_metrics()
write_to_log('Завершение сбора метрик')




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
#         write_to_log('Oтсутствуют аргументы')
