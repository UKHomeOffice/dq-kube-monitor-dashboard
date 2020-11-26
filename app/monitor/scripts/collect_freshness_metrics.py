
import os,sys,subprocess
import logging
import boto3
import psycopg2
import datetime
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
# temp_fms_list = []
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
    obtain CW logs filtered results by providing

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

        dbstatement_vio = """SELECT dv_load_dt FROM dq_fms.tbl_aviation_violations_status_by_schedule_stage WHERE "dv_load_dt" >= NOW() - INTERVAL '10 minutes' order by dv_load_dt desc"""
        dbstatement_con = """SELECT cs_lastupdated FROM dq_fms.tbl_consolidated_schedule WHERE "cs_lastupdated" >= NOW() - INTERVAL '10 minutes' order by cs_lastupdated desc"""
        # dbstatement = "select * from dq_fms.tbl_aviation_violations_status_by_schedule order by ssm_std_datetime_utc desc limit 5"
        #dbstatement = "SELECT DISTINCT file_name from dq_fms.stg_tbl_api"

        conn = psycopg2.connect(**conn_parameters)
        log.info('Connected to fms RDS')

        dbcur = conn.cursor()

        fms_vio_query = dbcur.execute(dbstatement_vio)
        fms_vio_rows = dbcur.fetchall()
        fms_con_query = dbcur.execute(dbstatement_con)
        fms_con_rows = dbcur.fetchall()

        if fms_vio_rows == []:
            fms_vio_status = 2
        else:
            fms_vio_status = 0

        if fms_con_rows == []:
            fms_con_status = 2
        else:
            fms_con_status = 0

        if (fms_vio_status == 0 and fms_con_status == 0):
            status = 0
        elif (bool(fms_vio_status == 0) ^ bool(fms_con_status == 0)):
            status = 1
        else:
            status = 2
        dic_item = { 'name': "fms_data" , 'status': status}
        fresh_dic_list.append(dic_item)
        log.info('Obtained the Freshness status of FMS data')
        dbcur.close()

    # except Exception as err:
    except:
        # log.error("there is an error connecting to fms db: ",err)
        dic_item = { 'name': "fms_data" , 'status': 2}
        fresh_dic_list.append(dic_item)
        print ("fms db error")

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

        dbstatement_fpl = """SELECT created_at FROM gama_fpl WHERE "created_at" >= NOW() - INTERVAL '5 minutes' order by created_at desc"""
        dbstatement_gar = """SELECT created_at FROM gama_gar WHERE "created_at" >= NOW() - INTERVAL '5 minutes' order by created_at desc"""

        conn = psycopg2.connect(**conn_parameters)
        log.info('Connected to GAIT RDS')

        dbcur = conn.cursor()

        fpl_query = dbcur.execute(dbstatement_fpl)
        fpl_rows = dbcur.fetchall()
        gar_query = dbcur.execute(dbstatement_gar)
        gar_rows = dbcur.fetchall()

        if fpl_rows == []:
            fpl_fresh_status = 2
        else:
            fpl_fresh_status = 0

        if gar_rows == []:
            gar_fresh_status = 2
        else:
            gar_fresh_status = 0

        if (fpl_fresh_status == 0 and gar_fresh_status == 0):
            status = 0
        elif (bool(fpl_fresh_status == 0) ^ bool(gar_fresh_status == 0)):
            status = 1
        else:
            status = 2
        dic_item = { 'name': "gait_data" , 'status': status}
        fresh_dic_list.append(dic_item)
        log.info('Obtained the Freshness status of GAIT data')
        dbcur.close()

    # except Exception as err:
    except Exception as e:
        # log.error("there is an error connecting to fms db: ",err)
        dic_item = { 'name': "gait_data" , 'status': 2}
        fresh_dic_list.append(dic_item)
        print ("gait db error: ",e)

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

# def obtainn_bfdp_fresh():
#
#     x=datetime.today()
#     y = x.replace(day=x.day, hour=1, minute=0, second=0, microsecond=0) - timedelta(days=1)
#     delta_t=y-x

def service_status_list():
    """
    create a list of services and the 2 or 0 code
    """

    # fresh_dic_list = []
    # dic_item  = {}

    log.info("Starting to fetch the freshness of each service....")
    fresh_dic_list.clear()
    obtain_fms_fresh()
    obtain_gait_fresh()
    obtain_drt_fresh()

    return fresh_dic_list
