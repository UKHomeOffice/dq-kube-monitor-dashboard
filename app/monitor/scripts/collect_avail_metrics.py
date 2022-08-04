
import os,sys,subprocess
import ssl
import json
import time
import logging
import requests
import datetime
import boto3

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
    {"name": "tab", "url": os.environ.get('TAB_URL'), "server": 'http://127.0.0.1:5000'},
    {"name": "exttab", "url": os.environ.get('EXTTAB_URL'), "server": 'http://127.0.0.1:5004'}
    ]

api_pod_list = [
    {"name": "gait_api", "url": 'http://dq-gait-api-data-consumer:6066', "pod": "dq-gait-api-data-consumer"},
    {"name": "gait_sgar", "url": 'http://dq-gait-sgar-consumer:6066', "pod": "dq-gait-sgar-consumer"},
    {"name": "api-msk", "url": 'http://dq-api-msk-consumer:6066', "pod": "dq-api-msk-consumer"}
]

lambda_func_list = [
    {"name": "drt_ath", "func_name": os.environ.get('DRT_ATH_GRP'), "log_intrv": 60},
    {"name": "drt_jsn", "func_name": os.environ.get('DRT_JSN_GRP'), "log_intrv": 360},
    {"name": "drt_rds", "func_name": os.environ.get('DRT_RDS_GRP'), "log_intrv": 360},
    {"name": "bf_api_parsed", "func_name": os.environ.get('BF_API_PRS'), "log_intrv": 30},
    {"name": "bf_api_raw", "func_name": os.environ.get('BF_API_RAW'), "log_intrv": 30},
    {"name": "bf_sch_cns", "func_name": os.environ.get('BF_SCH_CNS'), "log_intrv": 60},
    {"name": "bf_sch_acl", "func_name": os.environ.get('BF_SCH_ACL'), "log_intrv": 1440},
    {"name": "bf_sch_fs", "func_name": os.environ.get('BF_SCH_FS'), "log_intrv": 1440},
    {"name": "bf_sch_oag", "func_name": os.environ.get('BF_SCH_OAG'), "log_intrv": 60},
    {"name": "bf_xrs_ath", "func_name": os.environ.get('BF_XRS_ATH'), "log_intrv": 60},
    {"name": "bf_rls_ath", "func_name": os.environ.get('BF_RLS_ATH'), "log_intrv": 60},
    {"name": "bf_asr_ath", "func_name": os.environ.get('BF_ASR_ATH'), "log_intrv": 1440},
    {"name": "bf_as_ath", "func_name": os.environ.get('BF_AS_ATH'), "log_intrv": 1440}
    ]

fms_cert = '/APP/auth-files/fms_cert'
fms_key = '/APP/auth-files/fms_key'
avail_dic_list = []
avail_api_pod_list = []
lambda_list = []
lam_list = []
lam_info_list = []
dic_item  = {}
lambda_item = {}


# slack  message function
def alert_to_slack(service, status_code, check_type):
    """
    Formats the text and posts to a specific Slack web app's URL
    Returns:
        Slack API repsonse
    """

    try:
        url = os.environ.get('SLACK_URL')
        message = "*Error Code:* " + str(status_code)
        title = ":fire: :sad_parrot: *"+service+"* is Not Reachable :sad_parrot: :fire:"
        slack_data = {
            "text": title,
            "attachments": [
                {
                    "text": "{0}".format(message),
                    "color": "#B22222",
                    "attachment_type": "default",
                    "fields": [
                        {
                            "title": "Priority",
                            "value": "High",
                            "short": "false"
                        }
                    ],
                    "footer": "Kubernetes API",
                    "footer_icon": "https://platform.slack-edge.com/img/default_application_icon.png"
                }
            ]
            }

        headers = {'Content-Type': "application/json"}
        response = requests.post(url, data=json.dumps(slack_data), headers=headers)
        log.info('notification sent to Slack')

    except Exception as err:
        print('The following error has occurred while sending slack message: ',err)

# Setting log to STOUT
def obtain_http_code(url_name, url, server):
    """
    Obtain the http status code of each services
    and then convert it to 0 or 2
    """
    server_info=""
    # Obtain http code for front end
    try:
        if url_name == 'fms':
            http_status = requests.get(url, cert=(fms_cert, fms_key)).status_code
        elif url_name == 'crt':
            http_status = requests.get(url).status_code
        elif url_name == 'tab' or url_name == 'exttab':
            http_status = requests.get(url).status_code
        else:
            http_status = requests.get(url).status_code

    except requests.exceptions.RequestException as e:
        http_status = 000
        print(url_name, "http status code check error:" ,e)

    # obtain service status on pod
    try:
        if url_name == 'fms':
            server_status = requests.get(server).status_code
        elif url_name == 'crt':
            server_status = 200
        elif url_name == 'tab' or url_name == 'exttab':
            server_info = requests.get(server+"/admin/systeminfo.xml").text
            pattern1 = "<service status=\"Active\"/>"
            pattern2 = "<service status=\"Busy\"/>"
            if pattern1 in server_info or pattern2 in server_info:
                server_status = 200
            else:
                server_status = 400
        else:
            server_status = requests.get(server).status_code

    except requests.exceptions.RequestException as e:
        server_status = 000
        print(url_name, "Service on pod status check error:" ,e)

    if (http_status == 200 and server_status == 200):
        status = 0
    if http_status != 200:
        status = 1
        if url_name == 'tab':
            alert_to_slack('Internal Tableau Frontend',http_status,'avail')
        elif url_name == 'exttab':
            alert_to_slack('External Tableau Frontend',http_status,'avail')
        else:
            alert_to_slack(url,http_status,'avail')
    if server_status != 200:
        status = 1
        if url_name == 'tab':
            alert_to_slack('Internal Tableau Service',server_info,'avail')
        elif url_name == 'exttab':
            alert_to_slack('External Tableau Service',server_info,'avail')
        else:
            alert_to_slack('Service hosting '+server,server_status,'avail')
    if (http_status != 200 and server_status != 200):
        status = 2

    dic_item = { 'name': url_name , 'status': status}
    avail_dic_list.append(dic_item)
    log.info("Obtained the Availability status of "+url_name)

def obtain_api_pod_avail():

    for pod in api_pod_list:
        try:
            http_status = requests.get(pod['url']).text
            if 'OK' in http_status:
                status = 0
            else:
                status = 2
                # alert_to_slack(pod['pod'],http_status,'avail')
            dic_item = { 'name': pod['name'], 'status': status}
            avail_api_pod_list.append(dic_item)

        except Exception as err:
            dic_item = { 'name': pod['name'] , 'status': 2}
            avail_api_pod_list.append(dic_item)
            print(err)

def obtain_lambda_avail(lambda_name,func_name,log_intrv):
    """
    obtain the lambda functions State & if they are
    running without errors
    """
    try:
        lam_list.clear()
        lam_info_list.clear()
        timenow = datetime.datetime.now()
        timemin = datetime.datetime.now() - datetime.timedelta(minutes=log_intrv)
        time10min = datetime.datetime.now() - datetime.timedelta(minutes=10)
        timenowconv = timenow.timestamp() * 1000.0
        timeminconv = timemin.timestamp() * 1000.0
        time10minconv = time10min.timestamp() * 1000.0
        lambda_logs = boto3.client('logs',  region_name="eu-west-2")
        paginator = lambda_logs.get_paginator('filter_log_events')
        filter_1 = paginator.paginate(logGroupName='/aws/lambda/'+func_name,
                                                filterPattern='ERROR', startTime=int(time10minconv),
                                                endTime=int(timenowconv))
        filter_2 = paginator.paginate(logGroupName='/aws/lambda/'+func_name,
                                                filterPattern='Fail', startTime=int(time10minconv),
                                                endTime=int(timenowconv))
        filter_3 = paginator.paginate(logGroupName='/aws/lambda/'+func_name,
                                                filterPattern='fail', startTime=int(time10minconv),
                                                endTime=int(timenowconv))
        info_logs = paginator.paginate(logGroupName='/aws/lambda/'+func_name,
                                                filterPattern='INFO', startTime=int(timeminconv),
                                                endTime=int(timenowconv))

        for page in filter_1:
            for i in page['events']:
                lam_list.append(i['message'])
        for page in filter_2:
            for i in page['events']:
                lam_list.append(i['message'])
        for page in filter_3:
            for i in page['events']:
                lam_list.append(i['message'])
        for page in info_logs:
            for i in page['events']:
                lam_info_list.append(i['message'])

        if lam_list == [] and lam_info_list != []:
            lambda_health = 0
        if lam_info_list == []: #This indicates the pipline was not active for X mins
            lambda_health = 2
        if lam_list != []:
            lambda_health = 2

        lambda_item = { 'name': lambda_name , 'status': lambda_health}
        lambda_list.append(lambda_item)
        log.info("Obtained the Availability status of "+lambda_name)

    except Exception as err:
        lambda_item = { 'name': lambda_name , 'status': 2}
        lambda_list.append(lambda_item)
        print(err)

def lambda_avail_check():
    for lam in lambda_func_list:
        obtain_lambda_avail(lam['name'],lam['func_name'],lam['log_intrv'])

    for lam in lambda_list:
        if lam['name'] == 'drt_ath':
            drt_ath = lam['status']
        if lam['name'] == 'drt_jsn':
            drt_jsn = lam['status']
        if lam['name'] == 'drt_rds':
            drt_rds = lam['status']
        if lam['name'] == 'bf_api_parsed':
            bf_api_parsed = lam['status']
        if lam['name'] == 'bf_api_raw':
            bf_api_raw = lam['status']
        if lam['name'] == 'bf_sch_cns':
            bf_sch_cns = lam['status']
        if lam['name'] == 'bf_sch_acl':
            bf_sch_acl = lam['status']
        if lam['name'] == 'bf_sch_fs':
            bf_sch_fs = lam['status']
        if lam['name'] == 'bf_sch_oag':
            bf_sch_oag = lam['status']
        if lam['name'] == 'bf_xrs_ath':
            bf_xrs_ath = lam['status']
        if lam['name'] == 'bf_rls_ath':
            bf_rls_ath = lam['status']
        if lam['name'] == 'bf_asr_ath':
            bf_asr_ath = lam['status']
        if lam['name'] == 'bf_as_ath':
            bf_as_ath = lam['status']

    if drt_jsn == 0 and drt_rds == 0 and drt_ath == 0:
        drt_status = 0
    if drt_jsn != 0:
        drt_status = 1
    if drt_rds != 0:
        drt_status = 1
    if drt_ath != 0:
        drt_status = 1
    if drt_jsn != 0 and drt_rds != 0 and drt_ath != 0:
        drt_status = 2

    dic_item = { 'name': "drt" , 'status': drt_status}
    avail_dic_list.append(dic_item)
    log.info("Obtained the Availability status of DRT")

    # bf api files
    ## Obtain APi pods availability first
    obtain_api_pod_avail()
    for pod in avail_api_pod_list:
        if pod['name'] == 'gait_api':
            api_gait = pod['status']
        if pod['name'] == 'api-msk':
            api_msk = pod['status']
        if pod['name'] == 'gait_sgar':
            api_sgar = pod['status']

    ## Obtain api lambdas avial
    if bf_api_parsed == 0 and bf_api_raw == 0 and api_gait == 0 and api_msk == 0 and api_sgar == 0:
        bf_api_status = 0
    if bf_api_parsed != 0:
        bf_api_status = 1
    if bf_api_raw != 0:
        bf_api_status = 1
    if api_gait != 0:
        bf_api_status = 1
    if api_msk != 0:
        bf_api_status = 1
    if api_sgar != 0:
        bf_api_status = 1
    if bf_api_parsed != 0 and bf_api_raw != 0 and api_gait != 0 and api_msk != 0 and api_sgar != 0:
        bf_api_status = 2

    dic_item = { 'name': "bf_api" , 'status': bf_api_status}
    avail_dic_list.append(dic_item)
    log.info("Obtained the Availability status of BFDP API")

    # bf scoring  files
    if (bf_xrs_ath == 0 and bf_rls_ath == 0 and bf_asr_ath == 0 and bf_as_ath == 0):
        bf_scr_status = 0
    if bf_xrs_ath != 0:
        bf_scr_status = 1
    if bf_rls_ath != 0:
        bf_scr_status = 1
    if bf_asr_ath != 0:
        bf_scr_status = 1
    if bf_as_ath != 0:
        bf_scr_status = 1
    if bf_xrs_ath != 0 and bf_rls_ath != 0 and bf_asr_ath != 0 and bf_as_ath != 0:
        bf_scr_status = 2

    dic_item = { 'name': "bf_scr" , 'status': bf_scr_status}
    avail_dic_list.append(dic_item)
    log.info("Obtained the Availability status of BFDP SCR")

    #  bf Scheduling state
    if (bf_sch_fs == 0 and bf_sch_cns == 0 and bf_sch_acl == 0 and bf_sch_oag == 0):
        bf_sch_status = 0
    if bf_sch_fs != 0:
        bf_sch_status = 1
    if bf_sch_cns != 0:
        bf_sch_status = 1
    if bf_sch_acl != 0:
        bf_sch_status = 1
    if bf_sch_oag != 0:
        bf_sch_status = 1
    if bf_sch_fs != 0 and bf_sch_cns != 0 and bf_sch_acl != 0 and bf_sch_oag != 0:
        bf_sch_status = 2

    dic_item = { 'name': "bf_sch" , 'status': bf_sch_status}
    avail_dic_list.append(dic_item)
    log.info("Obtained the Availability status of BFDP SCH")

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
