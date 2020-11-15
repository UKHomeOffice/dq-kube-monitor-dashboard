#!/bin/bash
# Wrapper script to run both prom_web_expose.py and collect_avail_metrics.py on startup

exec python /APP/scripts/prom_web_expose.py &
exec python /APP/scripts/monitor_wrapper.py
