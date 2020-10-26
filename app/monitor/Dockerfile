FROM quay.io/ukhomeofficedigital/python-alpine:3.7.6-alpine3.11

LABEL maintainer="dqdevops@digital.homeoffice.gov.uk"

ENV USERMAP_UID 1000

WORKDIR /APP

RUN apk add --no-cache --quiet --update

RUN mkdir -p /APP/scripts

COPY scripts/collect_avail_metrics.py /APP/scripts/collect_avail_metrics.py && \
chmod +x /APP/scripts/scripts/collect_avail_metrics.py

COPY scripts/prom_web_expose.py /APP/scripts/prom_web_expose.py && \
chmod +x /APP/scripts/scripts/prom_web_expose.py

COPY scripts/run.sh /APP/scripts/run.sh && \
chmod +x /APP/scripts/scripts/run.sh

RUN adduser -D -H 1000 && chown -R 1000 /APP

RUN pip install boto3 schedule requests

EXPOSE 8000

USER ${USERMAP_UID}

CMD sh /APP/scripts/run.sh
