FROM python:3.8.6-alpine3.12

LABEL maintainer="dqdevops@digital.homeoffice.gov.uk"

ENV USERMAP_UID 1000
WORKDIR /APP

RUN apk add --no-cache --quiet --update

RUN apk --no-cache add curl \
g++ \
gcc \
libxslt-dev \
postgresql-dev \
build-base \
bash \
linux-headers \
pcre-dev

RUN mkdir -p /APP/scripts

COPY app/monitor/scripts/ /APP/scripts

RUN adduser -D -H 1000 && chown -R 1000 /APP

RUN chmod -R +x /APP/scripts

RUN pip install boto3 schedule requests psycopg2

EXPOSE 8000

USER ${USERMAP_UID}

CMD sh ./scripts/run.sh
