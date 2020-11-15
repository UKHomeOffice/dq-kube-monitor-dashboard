import os,sys,subprocess
import json
import time
import logging
import schedule
from collect_avail_metrics import service_status_list as a
from collect_freshness_metrics import service_status_list as f

log = logging.getLogger(__name__)
out_hdlr = logging.StreamHandler(sys.stdout)
out_hdlr.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
out_hdlr.setLevel(logging.INFO)
log.addHandler(out_hdlr)
log.setLevel(logging.INFO)

def write_to_json():
    """
    create the tarcing.json file the will be grabed by the
    prometheous agent to be sent to sysdig
    """
    try:
        f = open("/APP/scripts/tracing.json", "w")
        print("a.avail_dic_list is: ",a())
        for item in a():
            f.write("# HELP availability_of_"+item['name']+ " to check the URL uptime \n")
            f.write("dq_"+item['name']+"_availability " +str(item['status'])+ "\n")
        print("f.fresh_dic_list is: ",f())
        for item in f():
            f.write("# HELP availability_of_"+item['name']+ " to check the URL uptime \n")
            f.write("dq_"+item['name']+"_freshness " +str(item['status'])+ "\n")
        f.close()
        log.info("File created")
    except Exception as e:
        log.error(e)



def main():
    log.info("Starting Scheduler......")
    # schedule.every(1).minutes.at(":00").do(service_status_list)
    schedule.every(2).minutes.at(":00").do(write_to_json)
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__== "__main__":
    main()
