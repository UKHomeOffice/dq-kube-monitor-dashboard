#!/usr/bin/env bash

set +x

# Attach host network to allow DNS resolution via local DNS resolution service
docker build --network=host \
  -t dq-monitor:dev1 \
  -f app/monitor/Dockerfile \
  ./
