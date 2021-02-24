FROM python:3.8.6-alpine3.12

LABEL maintainer="dqdevops@digital.homeoffice.gov.uk"

ENV USERMAP_UID 1000
WORKDIR /APP

RUN mkdir -p /APP/scripts

COPY app/scripts/ /APP/scripts/

RUN apk add --no-cache --quiet --update

RUN apk add nginx

RUN adduser -D -H 1000 && \
    chown -R 1000 /APP && \
    chown -R 1000 /home/www/

RUN chmod -R +x scripts/

RUN pip install boto3 schedule requests

USER ${USERMAP_UID}

EXPOSE 8000
EXPOSE 80

CMD [".scripts/run.sh"]
