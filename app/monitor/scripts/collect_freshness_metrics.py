
import os,sys,subprocess
import logging
import boto3
import psycopg2
import time
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

fresh_dic_list = []
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
        ssm = boto3.client('ssm', region_name="eu-west-2")
        response = ssm.get_parameters(
            Names=param_name_list,
            WithDecryption=True)
        values = {}
        for param in response['Parameters']:
            if param['Name'] == '/rds_fms_username':
                values['user'] = param['Value']
            elif param['Name'] == '/rds_fms_password':
                values['pass'] = param['Value']
        return values
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

        dbstatement_vio = """SELECT dv_load_dt FROM dq_fms.tbl_aviation_violations_status_by_schedule_stage WHERE "dv_load_dt" >= NOW() - INTERVAL '5 minutes' order by dv_load_dt desc"""
        dbstatement_con = """SELECT cs_lastupdated FROM dq_fms.tbl_consolidated_schedule WHERE "cs_lastupdated" >= NOW() - INTERVAL '5 minutes' order by cs_lastupdated desc"""

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

    except Exception as err:
        # log.error("there is an error connecting to fms db: ",err)
        dic_item = { 'name': "fms_data" , 'status': 2}
        fresh_dic_list.append(dic_item)
        print (err)

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
            'port': '8082',
            'dbname': 'dqgaitrds2',
            'user': values['user'],
            'password': values['pass'],
            'sslmode': 'require',
            'options': '-c statement_timeout=60000'
        }

        dbstatement_fpl = """SELECT created_at FROM gama_fpl WHERE "created_at" >= NOW() - INTERVAL '5 minutes' order by created_at desc"""
        dbstatement_gar = """SELECT created_at FROM gama_gar WHERE "created_at" >= NOW() - INTERVAL '5 minutes' order by created_at desc"""

        conn = psycopg2.connect(**conn_parameters)
        log.info('Connected to fms RDS')

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

    except Exception as err:
        # log.error("there is an error connecting to fms db: ",err)
        dic_item = { 'name': "gait_data" , 'status': 2}
        fresh_dic_list.append(dic_item)
        print (err)

def service_status_list():
    """
    create a list of services and the 2 or 0 code
    """

    fresh_dic_list = []
    dic_item  = {}

    log.info("Starting to fetch the freshness of each service....")
    fresh_dic_list.clear()
    obtain_fms_fresh()
    obtain_gait_fresh()

    return fresh_dic_list
