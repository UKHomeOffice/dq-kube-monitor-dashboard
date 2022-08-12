import boto3
import os,sys,subprocess
import logging
import datetime
import time
import requests
import json

#Setting log to STOUT
log = logging.getLogger(__name__)
out_hdlr = logging.StreamHandler(sys.stdout)
out_hdlr.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
out_hdlr.setLevel(logging.INFO)
log.addHandler(out_hdlr)
log.setLevel(logging.INFO)

athena_query_results = []
dic_item  = {}

conn_parameters = {
    "region": "eu-west-2",
    "database":"api_record_level_score_"+os.environ.get('ENV'),
    "bucket": "s3-dq-athena-log-"+os.environ.get('ENV'),
    "path": "workbench-bastion"
}

day = datetime.datetime.today()
prevday = day - datetime.timedelta(days=1)
prevday = prevday.strftime("%Y%m%d")

def get_ssm_parameters(param_name_list,conn_parameters):
    """
    Returns parameter values from AWS SSM

    Args:
        param_name_list : a list of parameter names

    Returns:
       A dict containing the parameter names and their values
    """
    try:
        ssm = boto3.client('ssm',
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            region_name=conn_parameters["region"])
        response = ssm.get_parameters(
            Names=param_name_list,
            WithDecryption=True)
        values = {}
        for param in response['Parameters']:
            if "id" in param['Name']:
                values['user'] = param['Value']
            elif "key" in param['Name']:
                values['pass'] = param['Value']
        return values
    except Exception as err:
        print(err)

# slack  message function
def alert_to_slack(day, no_zips, last_zip):
    """
    Formats the text and posts to a specific Slack web app's URL
    Returns:
        Slack API repsonse
    """
    try:
        url = os.environ.get('SLACK_URL')
        message1 ="The *No PARSED zip* files for *"+day+"* is: \n"+no_zips
        message2 ="The *last zip file* recieved for *"+day+"* is: \n"+last_zip

        title = ":fire: :sad_parrot: API PARSED Zip Files Count :sad_parrot: :fire:"
        slack_data = {
                      "blocks": [
                        {
                          "type": "header",
                          "text": {
                            "type": "plain_text",
                            "text": title
                          }
                        },
                        {
                          "type": "section",
                          "text": {
                            "type": "mrkdwn",
                            "text": message1
                          }
                        },
                        {
                          "type": "section",
                          "text": {
                            "type": "mrkdwn",
                            "text": message2
                          }
                        }
                      ]
                    }


        headers = {'Content-Type': "application/json"}
        response = requests.post(url, data=json.dumps(slack_data), headers=headers)
        log.info('notification sent to Slack')

    except Exception as err:
        print('The following error has occurred while sending slack message: ',err)

def athena_query(client,query,conn_parameters):
    """
    Query the internal_tableau Athena DB
    """

    try:
        execution = client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={
            'Database': conn_parameters['database']
        },
        ResultConfiguration={
            'OutputLocation': 's3://' + conn_parameters['bucket'] + '/' + conn_parameters['path']
            }
        )
        execution_id = execution['QueryExecutionId']
        state = 'RUNNING'
        while (state in ['RUNNING', 'QUEUED']):
            response = client.get_query_execution(QueryExecutionId = execution_id)
            if 'QueryExecution' in response and \
                    'Status' in response['QueryExecution'] and \
                    'State' in response['QueryExecution']['Status']:
                state = response['QueryExecution']['Status']['State']
                if state == 'FAILED':
                    return False
                elif state == 'SUCCEEDED':
                    log.info('Athena query ('+query+') successfully completed')
                    result = client.get_query_results(QueryExecutionId = execution_id)
                    return result
            time.sleep(1)

    except Exception as e:
        print ("Athena connection error: ",e)

def obtain_zip_count(client,dayformat):
    """
    Pass the SQL queries to Athena
    """
    athena_query_results.clear()
    query_list = [
        {"name": "no_zips", "query": "select count(distinct file_name) from api_record_level_score_prod.internal_storage where file_name like '%PARSED_"+dayformat+"%'"},
        {"name": "last_zip", "query": "select max(distinct file_name) from api_record_level_score_prod.internal_storage where file_name like '%PARSED_"+dayformat+"%'"}
    ]

    for item in query_list:
        query_result=athena_query(client,item['query'],conn_parameters)
        result=query_result['ResultSet']['Rows'][1]['Data'][0]['VarCharValue']
        dic_item = {'name': item['name'], 'query_result': result}
        athena_query_results.append(dic_item)

    return athena_query_results

def query_results():
    """
    create a list of query results
    """
    values = get_ssm_parameters(
        ["/tableau-athena-user-default-id-apps-"+os.environ.get('ENV')+"-dq",
         "/tableau-athena-user-default-key-apps-"+os.environ.get('ENV')+"-dq"],conn_parameters)

    session = boto3.Session(
        aws_access_key_id=values['user'],
        aws_secret_access_key=values['pass']
    )

    client = session.client('athena', region_name=conn_parameters["region"])

    obtain_zip_count(client,prevday)

    return athena_query_results

def send_alert():
    """
    Send slack alert if No of zips not matching
    last file seq number
    """
    values = get_ssm_parameters(
        ["/tableau-athena-user-default-id-apps-"+os.environ.get('ENV')+"-dq",
         "/tableau-athena-user-default-key-apps-"+os.environ.get('ENV')+"-dq"],conn_parameters)

    session = boto3.Session(
        aws_access_key_id=values['user'],
        aws_secret_access_key=values['pass']
    )

    client = session.client('athena', region_name=conn_parameters["region"])

    obtain_zip_count(client,prevday)

    # send the results to slack
    no_zips = athena_query_results[0]['query_result']
    last_zip = athena_query_results[1]['query_result']

    # send alert iff no_zips is less han 1440
    parts = last_zip.split(".")
    zip_name = parts[0].split("_")
    seq_of_lastzip = zip_name[4]

    if int(no_zips) != int(seq_of_lastzip):
        alert_to_slack(prevday, no_zips, last_zip)
