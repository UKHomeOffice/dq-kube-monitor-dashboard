FROM quay.io/ukhomeofficedigital/python-alpine:3.7.6-alpine3.11

LABEL maintainer="dqdevops@digital.homeoffice.gov.uk"

ENV USERMAP_UID 1000

WORKDIR /APP

RUN apk add --no-cache --quiet --update

RUN mkdir -p /APP/scripts

ADD scripts /APP/scripts/

RUN adduser -D -H 1000 && chown -R 1000 /APP

RUN chmod -R +x /APP/scripts/

RUN pip install boto3 schedule requests

EXPOSE 8000

USER ${USERMAP_UID}

CMD [".scripts/run.sh"]
