FROM python:3.12.0b3-alpine3.18

LABEL maintainer="dqdevops@digital.homeoffice.gov.uk"

ENV USERMAP_UID 1000
WORKDIR /APP

RUN apk update --quiet \
      && apk upgrade --quiet \
      && apk add --no-cache --quiet --update

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

COPY app/monitor/scripts/ /APP/scripts/

RUN adduser -D -H 1000 && chown -R 1000 /APP

RUN chmod -R +x /APP/scripts

RUN pip install --no-cache-dir --upgrade pip==25.3 && pip install boto3 schedule requests psycopg2 urllib3
# Upgrade force wheel to latest (or pin exactly to 0.46.2+)
RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir --upgrade --force-reinstall "wheel==0.46.2" setuptools \
    && pip show wheel

EXPOSE 8000

USER ${USERMAP_UID}

CMD sh ./scripts/run.sh
