
import os,sys,subprocess
import logging
import boto3
import psycopg2
import datetime
import requests
import xml.etree.cElementTree as et
# from botocore.config import Config
#
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

active_region = 'eu-west-2'
fresh_dic_list = []
rds_list = []
json_list = []
dic_item  = {}

def get_ssm_parameters(param_name_list):
    """
    Returns parameter values from AWS SSM

    Args:
        param_name_list : a list of parameter names

    Returns:
       A dict containing the parameter names and their values
    """
    try:
        ssm = boto3.client('ssm', region_name=active_region)
        response = ssm.get_parameters(
            Names=param_name_list,
            WithDecryption=True)
        values = {}
        for param in response['Parameters']:
            if "name" in param['Name']:
                values['user'] = param['Value']
            elif "password" in param['Name']:
                values['pass'] = param['Value']
        return values
    except Exception as err:
        print(err)

def log_filter_pagi(log_group,min,filter):
    """
    Obtain CW logs filtered results by providing

    log_group: (string) log group name
    min: (intiger) No of minutes for logs to be parsed for the provided filter
    filter: (string) value matching the text to search/pasre the log group for
    """
    try:
        timenow = datetime.datetime.now()
        timebefore = datetime.datetime.now() - datetime.timedelta(minutes=min)
        timenowconv = timenow.timestamp() * 1000.0
        timebeforeconv = timebefore.timestamp() * 1000.0

        lambda_logs = boto3.client('logs', region_name=active_region)
        paginator = lambda_logs.get_paginator('filter_log_events')
        pages = paginator.paginate(logGroupName='/aws/lambda/'+log_group,
                                                filterPattern=filter, startTime=int(timebeforeconv),
                                                endTime=int(timenowconv))
        return pages

    except Exception as err:
        print(err)

def obtain_fms_fresh():
    """
    Query the fms RDS DB for new rows
    in the fms table
    """
    try:
        values = get_ssm_parameters(
            ['/rds_fms_username',
             '/rds_fms_password'])

        conn_parameters = {
            'host': '127.0.0.1',
            'port': '5001',
            'dbname': 'fms',
            'user': values['user'],
            'password': values['pass'],
            'sslmode': 'require',
            'options': '-c statement_timeout=60000'
        }

        day = datetime.datetime.today()
        nextday = day + datetime.timedelta(days=1)
        prevday = day - datetime.timedelta(days=1)
        today = day.strftime("%Y-%m-%d")
        nextday = nextday.strftime("%Y-%m-%d")
        prevday = prevday.strftime("%Y-%m-%d")

        # to allow for low number of flights in teh early mornings
        now = datetime.datetime.now()
        if now.hour >= 0 and now.hour < 6:
            day1 = prevday
            day2 = today
        else:
            day1 = today
            day2 = nextday

        dbstatement = "select count (voyage_number) from dq_fms.tbl_aviation_violations_status_by_schedule where ssm_std_datetime_utc >= '"+day1+" 00:00:00' AND  ssm_std_datetime_utc < '"+day2+" 00:00:00'"
        conn = psycopg2.connect(**conn_parameters)
        log.info('Connected to FMS RDS DB')

        dbcur = conn.cursor()
        fms_query = dbcur.execute(dbstatement)
        fms_rows = dbcur.fetchall()
        result = str(fms_rows[0])[1:-2]

        if int(result) >= 5:
            fms_fresh_status = 0
        elif (int(result) < 5 and int(result) >=3):
            fms_fresh_status = 1
        else:
            fms_fresh_status = 2

        dic_item = { 'name': "fms_data" , 'status': fms_fresh_status}
        fresh_dic_list.append(dic_item)

        log.info('Obtained the Freshness status of FMS data')
        dbcur.close()

    except Exception as e:
        dic_item = { 'name': "fms_data" , 'status': 2}
        fresh_dic_list.append(dic_item)
        print ("fms db connection error", e)

# def final_fms_check():
#     temp_fms_list.clear()
#     dic_item = {}
#     fms_error=0
#     for i in range(3):
#         obtain_fms_fresh()
#         time.sleep(120)
#     for j in temp_fms_list:
#         if j['status'] == 2:
#             fms_error++1
#     if fms_error == 3:
#         dic_item = { 'name': "fms_data" , 'status': 2}
#     else:
#         dic_item = { 'name': "fms_data" , 'status': 0}
#     fresh_dic_list.append(dic_item)

def obtain_gait_fresh():
    """
    Query the GAIT RDS DB for new rows

    """
    try:
        values = get_ssm_parameters(
            ['/rds_gait_username',
             '/rds_gait_password'])

        conn_parameters = {
            'host': '127.0.0.1',
            'port': '5002',
            'dbname': 'dqgaitrds2',
            'user': values['user'],
            'password': values['pass'],
            'sslmode': 'require',
            'options': '-c statement_timeout=60000'
        }

        dbstatement_60 = """SELECT created_at FROM gama_voyage WHERE "created_at" >= NOW() - INTERVAL '60 minutes' order by created_at desc"""
        dbstatement_120 = """SELECT created_at FROM gama_voyage WHERE "created_at" >= NOW() - INTERVAL '120 minutes' order by created_at desc"""


        conn = psycopg2.connect(**conn_parameters)
        log.info('Connected to GAIT RDS')

        dbcur = conn.cursor()

        query_60 = dbcur.execute(dbstatement_60)
        rows_60 = dbcur.fetchall()
        query_120 = dbcur.execute(dbstatement_120)
        rows_120 = dbcur.fetchall()

        if rows_60 != []:
            gait_fresh_status = 0
        elif rows_60 == []:
            gait_fresh_status = 1
        elif rows_120 == []:
            gait_fresh_status = 2

        dic_item = { 'name': "gait_data" , 'status': gait_fresh_status}
        fresh_dic_list.append(dic_item)
        log.info('Obtained the Freshness status of GAIT data')
        dbcur.close()

    except Exception as e:
        # log.error("there is an error connecting to fms db: ",err)
        dic_item = { 'name': "gait_data" , 'status': 2}
        fresh_dic_list.append(dic_item)
        print ("gait db connection error: ",e)

def obtain_drt_fresh():
    """
    Query DRT pipline for fiels pusheed top datafeed and
    JSON files to DRT S3
    """
    try:
        rds_list.clear()
        drt_rds = log_filter_pagi(os.environ.get('DRT_RDS_GRP'),5,'committed')
        for page in drt_rds:
            for i in page['events']:
                if not '0 rows' in i['message']:
                    rds_list.append(i['message'])
        if rds_list == []:
            drt_rds_status = 2
        else:
            drt_rds_status = 0

        json_list.clear()
        drt_json = log_filter_pagi(os.environ.get('DRT_JSN_GRP'),15,'Total events')
        for page in drt_json:
            for i in page['events']:
                if 'Total events' in i['message']:
                    json_list.append(i['message'])
        if json_list == []:
            drt_json_status = 2
        else:
            drt_json_status = 0

        if (drt_rds_status == 0 and drt_json_status == 0):
            status = 0
        elif (bool(drt_rds_status == 0) ^ bool(drt_json_status == 0)):
            status = 1
        else:
            status = 2
        dic_item = { 'name': "drt_data" , 'status': status}
        fresh_dic_list.append(dic_item)
        log.info('Obtained the Freshness status of DRT data')

    except Exception as e:
        dic_item = { 'name': "drt_data" , 'status': 2}
        fresh_dic_list.append(dic_item)
        print ("DRT data error: ",e)

def obtainn_bfdp_fresh():
    """
    Query the internal_tableau RDS DB fto find out
    the timestamp of the last added entry
    """
    try:
        values = get_ssm_parameters(
            ['/rds_internal_tableau_username',
             '/rds_internal_tableau_password'])

        conn_parameters = {
            'host': '127.0.0.1',
            'port': '5003',
            'dbname': 'internal_tableau',
            'user': values['user'],
            'password': values['pass'],
            'sslmode': 'require',
            'options': '-c statement_timeout=60000'
        }

        dbstatement = "select last_message_datetime_received from rpt_internal.view_last_message_datetime_received"

        conn = psycopg2.connect(**conn_parameters)
        log.info('Connected to Internal Tableau RDS')

        dbcur = conn.cursor()
        query = dbcur.execute(dbstatement)
        rows = dbcur.fetchall()

        latest = str(rows[0])[1:-2]
        latest = eval(latest).strftime("%H:%M:%S")
        now = datetime.datetime.now()
        now = now.strftime("%H:%M:%S")
        FMT = '%H:%M:%S'
        tdelta = datetime.datetime.strptime(now, FMT) - datetime.datetime.strptime(latest, FMT)
        if tdelta.days < 0:
            tdelta = datetime.timedelta(days=0,seconds=tdelta.seconds, microseconds=tdelta.microseconds)

        sec = tdelta.total_seconds()
        minutes = int(sec // 60)

        if minutes <= 180:
            bfdp_data =  0
        elif (minutes > 180 and minutes <= 360):
            bfdp_data =  1
        elif minutes > 360:
            bfdp_data =  2

        dic_item = { 'name': "bfdp_data" , 'status': bfdp_data}
        fresh_dic_list.append(dic_item)
        log.info('Obtained the Freshness status of Internal Tableau data')

    except Exception as e:
        dic_item = { 'name': "bfdp_data" , 'status': 2}
        fresh_dic_list.append(dic_item)
        print ("Internal Tableau DB connection error: ",e)

def obtain_inttab_fresh():
    try:
        # Obtain the
        userdata = """
        <tsRequest>
        <credentials name="tab_admin" password="""+os.environ.get('TAB_ADMIN_PWD')+""">
                <site contentUrl="DQDashboards" />
        </credentials>
        </tsRequest>
        """
        tab_url = os.environ.get('TAB_URL')
        api_version = os.environ.get('TAB_API_VERSION')
        auth_url = tab_url+"/api/"+api_version+"/auth/signin"
        headers = {'Content-Type': 'application/xml'}
        req = requests.post(auth_url , data=userdata, headers=headers)
        root = et.fromstring(req.content)
        for child in root.iter('*'):
            if 'credentials' in child.tag:
                token = child.attrib.get('token')
            elif 'site' in child.tag:
                siteid = child.attrib.get('id')

        # Obtain the refresh jobs status
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        ref_url=tab_url+"/api/"+api_version+"/sites/"+siteid+"/jobs?filter=startedAt:gt:"+today+"T00:00:00z"
        ref_req = requests.get(ref_url , headers={'X-Tableau-Auth': token})
        root_ref = et.fromstring(ref_req.content)
        for child in root_ref.iter('*'):
            if 'backgroundJob' in child.tag:
                 count = count++1
                 jobid = child.attrib.get('id')
                 jobstatus = child.attrib.get('status')
                 jobtype = child.attrib.get('jobType')
                 if jobstatus == "Success":
                     tab_data = 0
                 elif jobstatus == "Running" or jobstatus == "InProgress":
                     tab_data = 1
                 elif jobstatus == "Failed":
                     tab_data = 2

        dic_item = { 'name': "tab_data" , 'status': tab_data}
        fresh_dic_list.append(dic_item)
        log.info('Obtained the Freshness status of DQ Reporting Dash')

    except Exception as e:
        dic_item = { 'name': "tab_data" , 'status': 2}
        fresh_dic_list.append(dic_item)
        print ("DQ Reporting Dash connection error: ",e)

def service_status_list():
    """
    create a list of services and the 2, 1 or 0 code
    """

    log.info("Starting to fetch the freshness of each service....")
    fresh_dic_list.clear()
    obtain_fms_fresh()
    obtain_gait_fresh()
    obtain_drt_fresh()
    obtainn_bfdp_fresh()
    obtain_inttab_fresh()

    return fresh_dic_list
