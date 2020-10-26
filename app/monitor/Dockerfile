FROM quay.io/ukhomeofficedigital/python-alpine:3.7.6-alpine3.11

LABEL maintainer="dqdevops@digital.homeoffice.gov.uk"

ENV USERMAP_UID 1000
WORKDIR /APP

RUN apk add --no-cache --quiet --update

RUN mkdir -p /APP/scripts

COPY app/monitor/scripts/collect_avail_metrics.py /APP/scripts/

COPY app/monitor/scripts/prom_web_expose.py /APP/scripts/

COPY app/monitor/scripts/run.sh /APP/scripts/

RUN adduser -D -H 1000 && \
    chown -R 1000 /APP && \

RUN chmod -R +x scripts/

RUN pip install boto3 schedule requests

USER ${USERMAP_UID}

EXPOSE 8000

CMD [".scripts/run.sh"]
