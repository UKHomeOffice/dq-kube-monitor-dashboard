
import os,sys,subprocess
import logging
import boto3
import psycopg2
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

        dbstatement = "SELECT DISTINCT file_name from dq_fms.stg_tbl_api"

        conn = psycopg2.connect(**conn_parameters)
        LOGGER.info('Connected to fms RDS')

        dbcur = conn.cursor()

        fms_query = dbcur.execute(dbstatement)
        fms_rows = dbcur.fetchall()

        if fms_rows == []:
            fms_fresh_status = 2
        else:
            fms_fresh_status = 0

        dic_item = { 'name': "fms_data" , 'status': fms_fresh_status}
        fresh_dic_list.append(dic_item)
        LOGGER.info('Obtained the Freshness status of FMS data')

    except Exception as err:
        # log.error("there is an error connecting to fms db: ",err)
        dic_item = { 'name': "fms_data" , 'status': 2}
        fresh_dic_list.append(dic_item)
        print (err)


def service_status_list():
    """
    create a list of services and the 2 or 0 code
    """

    log.info("Starting to fetch the freshness of each service....")
    fresh_dic_list.clear()

    obtain_fms_fresh()
    # schedule.every(2).minutes.at(":00").do(obtain_fms_fresh)

    return fresh_dic_list
