
import os,sys,subprocess
import ssl
import json
import time
import logging
import requests
import datetime
import boto3

# from botocore.config import Config

# CONFIG = Config(
#     retries=dict(
#         max_attempts=20
#     )
# )

#Setting log to STOUT
log = logging.getLogger(__name__)
out_hdlr = logging.StreamHandler(sys.stdout)
out_hdlr.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
out_hdlr.setLevel(logging.INFO)
log.addHandler(out_hdlr)
log.setLevel(logging.INFO)

service_list= [
    {"name": "gait", "url": os.environ.get('GAIT_URL'), "server": 'http://ga-app-service:3000'},
    {"name": "fms", "url": os.environ.get('FMS_URL'), "server": 'http://fms:3000'},
    {"name": "crt", "url": os.environ.get('CRT_URL'), "server": 'http://crt-service:10443'},
    {"name": "tab", "url": os.environ.get('TAB_URL'), "server": os.environ.get('TAB_URL')}
    ]

lambda_func_list = [
    {"name": "drt_ath", "func_name": os.environ.get('DRT_ATH_GRP')},
    {"name": "drt_jsn", "func_name": os.environ.get('DRT_JSN_GRP')},
    {"name": "drt_rds", "func_name": os.environ.get('DRT_RDS_GRP')},
    {"name": "bf_api_parsed", "func_name": os.environ.get('BF_API_PRS')},
    {"name": "bf_api_raw", "func_name": os.environ.get('BF_API_RAW')},
    {"name": "bf_sch", "func_name": os.environ.get('BF_SCH')},

    {"name": "bf_xrs_ath", "func_name": os.environ.get('BF_XRS_ATH')},
    {"name": "bf_rls_ath", "func_name": os.environ.get('BF_RLS_ATH')},
    {"name": "bf_asr_ath", "func_name": os.environ.get('BF_ASR_ATH')},
    {"name": "bf_as_ath", "func_name": os.environ.get('BF_AS_ATH')}
    ]

fms_cert = '/APP/fms-certs/fms_cert'
fms_key = '/APP/fms-certs/fms_key'
avail_dic_list = []
lambda_list = []
dic_item  = {}
lambda_item = {}

#Setting log to STOUT
def obtain_http_code(url_name, url, server):
    """
    Obtain the http status code of each services
    and then convert it to 0 or 2
    """
    try:
        if url_name == 'fms':
            http_status = requests.get(url, cert=(fms_cert, fms_key)).status_code
            server_status = requests.get(server).status_code
        elif url_name == 'crt':
            http_status = requests.get(url).status_code
            server_status = 200
        elif url_name == 'tab':
            http_status = requests.get(url).status_code
            server_status = 200
            # server_info = requests.get(url+"/admin/systeminfo.xml").text
            # pattern = "<service status=\"Active\"/>"
            # if pattern in server_info:
            #     server_status = 200
            # else:
            #     server_status = 400
        else:
            http_status = requests.get(url).status_code
            server_status = requests.get(server).status_code

        if (http_status == 200 and server_status == 200):
        # if http_status == 200:
            status = 0
        elif (bool(http_status == 200) ^ bool(server_status == 200)):
            status = 1
        else:
            status = 2

        dic_item = { 'name': url_name , 'status': status}
        avail_dic_list.append(dic_item)
        log.info("Obtained the Availability status of "+url_name)

    # except requests.ConnectionError as e:
    except requests.exceptions.RequestException as e:
    # except:
        dic_item = { 'name': url_name , 'status': 2}
        avail_dic_list.append(dic_item)
        # log.error("Not able to obtain the Availability status of "+url_name)
        print(e)

def obtain_lambda_avail(lambda_name,func_name):
    """
    obtain the lambda functions State & if they are
    running without errors
    """
    timenow = datetime.datetime.now()
    time1min = datetime.datetime.now() - datetime.timedelta(minutes=1)
    timenowconv = timenow.timestamp() * 1000.0
    time1minconv = time1min.timestamp() * 1000.0
    lambda_logs = boto3.client('logs',  region_name="eu-west-2")

    filter = lambda_logs.filter_log_events(logGroupName='/aws/lambda/'+func_name,
                                            filterPattern='ERROR', startTime=int(time1minconv),
                                            endTime=int(timenowconv))
    message = filter['events']
    if message == []:
        lambda_health = 0
    else:
        lambda_health = 2

    # lambda_item = {lambda_name+'_health': lambda_health}
    lambda_item = { 'name': lambda_name , 'status': lambda_health}
    lambda_list.append(lambda_item)
    log.info("Obtained the Availability status of "+lambda_name)

def lambda_avail_check():
    for lam in lambda_func_list:
        obtain_lambda_avail(lam['name'],lam['func_name'])

    for lam in lambda_list:
        if lam['name'] == 'drt_ath':
            drt_ath_health = lam['status']
        if lam['name'] == 'drt_jsn':
            drt_jsn_health = lam['status']
        if lam['name'] == 'drt_rds':
            drt_rds_health = lam['status']
        if lam['name'] == 'bf_api_parsed':
            bf_api_parsed_health = lam['status']
        if lam['name'] == 'bf_api_raw':
            bf_api_raw_health = lam['status']
        if lam['name'] == 'bf_sch':
            bf_sch_health = lam['status']
        if lam['name'] == 'bf_xrs_ath':
            bf_xrs_ath_health = lam['status']
        if lam['name'] == 'bf_rls_ath':
            bf_rls_ath_health = lam['status']
        if lam['name'] == 'bf_asr_ath':
            bf_asr_ath_health = lam['status']
        if lam['name'] == 'bf_as_ath':
            bf_as_ath_health = lam['status']


    if (drt_jsn_health == 0 and drt_rds_health == 0 and drt_ath_health == 0):
        drt_status = 0
    elif ((bool(drt_jsn_health == 0) ^ bool(drt_rds_health == 0)) ^ bool(drt_ath_health == 0)):
        drt_status = 1
    else:
        drt_status = 2

    dic_item = { 'name': "drt" , 'status': drt_status}
    avail_dic_list.append(dic_item)
    log.info("Obtained the Availability status of DRT")

    # bf api files
    if (bf_api_parsed_health == 0 and bf_api_raw_health == 0):
        bf_api_status = 0
    elif (bool(bf_api_parsed_health == 0) ^ bool(bf_api_raw_health == 0)):
        bf_api_status = 1
    else:
        bf_api_status = 2

    # bf scoring  files
    if (bf_xrs_ath_health == 0 and bf_rls_ath_health == 0 and bf_asr_ath_health == 0 and bf_as_ath_health == 0):
        bf_scr_status =  0
    elif ((bool(bf_xrs_ath_health == 0) ^ bool(bf_rls_ath_health == 0)) ^ (bool(bf_asr_ath_health == 0) ^ bool(bf_as_ath_health == 0))):
        bf_scr_status =  1
    else:
        bf_scr_status =  2

    #  bf combined state
    if (bf_api_status == 0 and bf_sch_health == 0 and bf_scr_status == 0):
        bf_status = 0
    elif ((bool(bf_api_status == 0) ^ bool(bf_sch_health == 0)) ^ bool(bf_scr_status == 0)):
        bf_status = 1
    else:
        bf_status = 2

    dic_item = { 'name': "bfdp" , 'status': bf_status}
    avail_dic_list.append(dic_item)
    log.info("Obtained the Availability status of BFDP")

def service_status_list():
    """
    create a list of services and the 2 or 0 code
    """
    log.info("Starting to fetch the availability of each service....")
    avail_dic_list.clear()
    for service in service_list:
        obtain_http_code(service['name'], service['url'], service['server'])

    lambda_avail_check()

    return avail_dic_list
