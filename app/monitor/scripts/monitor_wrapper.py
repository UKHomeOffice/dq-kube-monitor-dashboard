import os,sys,subprocess
import json
import time
import logging
import schedule
from collect_avail_metrics import service_status_list as avail
from collect_freshness_metrics import service_status_list as fresh
from athena_queries import query_results as api_zips
from athena_queries import send_alert as api_count_alert

log = logging.getLogger(__name__)
out_hdlr = logging.StreamHandler(sys.stdout)
out_hdlr.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
out_hdlr.setLevel(logging.INFO)
log.addHandler(out_hdlr)
log.setLevel(logging.INFO)

fresh_list = []

# def retreive_fresh():
#     fresh_list = fresh()

def write_to_json():
    """
    create the tarcing.json file the will be grabed by the
    prometheous agent to be sent to sysdig
    """
    try:
        with open("/APP/scripts/tracing.json", "w") as f:
            print("avail_dic_list is: ",avail())
            for item in avail():
                f.write("# HELP availability_of_"+item['name']+ " to check service availability \n")
                f.write("dq_"+item['name']+"_availability " +str(item['status'])+ "\n")
            print("fresh_dic_list is: ",fresh())
            for item in fresh():
                f.write("# HELP freshness_of_"+item['name']+ " to check data freshness \n")
                f.write("dq_"+item['name']+"_freshness " +str(item['status'])+ "\n")
            print("The PARSED Zip file stats are: ",api_zips())
            for item in api_zips():
                f.write("# HELP PARSED API "+item['name']+" \n")
                f.write("dq_api_pasred_"+item['name']+" "+str(item['query_result'])+ "\n")
        log.info("File created")
    except Exception as e:
        log.error(e)


def main():
    log.info("Starting Scheduler......")
    schedule.every(7).minutes.at(":00").do(write_to_json)
    # schedule.every(10).minutes.at(":02").do(retrive_api_zips)
    schedule.every().day.at("08:33").do(api_count_alert)
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__== "__main__":
    main()
