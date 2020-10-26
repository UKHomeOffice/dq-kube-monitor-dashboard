
import os,sys,subprocess
import ssl
import json
import time
import logging
import requests
import datetime
import schedule

#Setting log to STOUT
log = logging.getLogger(__name__)
out_hdlr = logging.StreamHandler(sys.stdout)
out_hdlr.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
out_hdlr.setLevel(logging.INFO)
log.addHandler(out_hdlr)
log.setLevel(logging.INFO)

service_list= [
    {"name": "gait", "url": os.environ.get('GAIT_URL')},
    {"name": "fms", "url": os.environ.get('FMS_URL')},
    {"name": "crt", "url": os.environ.get('CRT_URL')}
        # {"name": "gait", "url": "http://ga-app-service:3000"},
        # {"name": "fms", "url": "http://fms:3000"},
        # {"name": "crt", "url": "http://crt-acp.notprod.dq.homeoffice.gov.uk"}
    ]

dic_list = []
dic_item  = {}
#Setting log to STOUT
def obtain_http_code(url_name, url):
    """
    Obtain the http status code of each services
    and then convert it to 1 or 0
    """
    try:
        http_status = requests.get(url).status_code
        if http_status == 200:
            status = 0
        else:
            status = 2
        dic_item = { 'name': url_name , 'status': status}
        dic_list.append(dic_item)
        log.info("Obtained the Availability status of "+url_name)

    except requests.ConnectionError as e:
        log.error(e)
        print(e)

def service_status_list():
    """
    create a list of services and the  2  or 0 code
    """
    log.info("Starting to fetch the availability of each service....")
    dic_list.clear()
    for service in service_list:
        obtain_http_code(service['name'], service['url'])

def write_to_json():
    """
    create the tarcing.json file the will be grabed by the
    prometheous agent to be sent to sysdig
    """
    try:
        f = open("/APP/scripts/tracing.json", "w")
        print("dic_list is: ",dic_list)
        for item in dic_list:
                f.write("# HELP availability_of_"+item['name']+ " to check the URL uptime \n")
                f.write("dq_"+item['name']+"_availability " +str(item['status'])+ "\n")
        f.close()
        log.info("File created")
    except Exception as e:
        log.error(e)

def main():
    log.info("Starting Scheduler......")
    schedule.every(1).minutes.at(":00").do(service_status_list)
    schedule.every(1).minutes.at(":30").do(write_to_json)
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__== "__main__":
    main()
