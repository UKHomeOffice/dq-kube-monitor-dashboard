# Deploying DQ Monitor

This project is to be used to deploy in the UK Home Office ACP and
therefore depends on certain features present in the platform. This repo creates a pod that checks the availability of the following DQ services and then make  the  availability metrics available  for  colelction by Sysdig  

## Introduction

This deployment will create 1 container in Kubernetes:-

* monitor - alpine python image
