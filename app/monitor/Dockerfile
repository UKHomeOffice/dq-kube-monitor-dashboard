FROM quay.io/ukhomeofficedigital/python-alpine:3.7.6-alpine3.11

LABEL maintainer="dqdevops@digital.homeoffice.gov.uk"

ENV USERMAP_UID 1000
WORKDIR /APP

RUN mkdir -p /APP/scripts

COPY app/monitor/scripts/* /APP/scripts/

RUN apk add --no-cache --quiet --update

RUN adduser -D -H 1000 && \
    chown -R 1000 /APP && \

RUN chmod -R +x scripts/

RUN pip install boto3 schedule requests

USER ${USERMAP_UID}

EXPOSE 8000

CMD [".scripts/run.sh"]
