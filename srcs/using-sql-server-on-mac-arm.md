---
title: Using SQL Server on my Mac M1
date: 2025-02-13
description: Let's run a docker container for SQL Server development even on mac m1
---

Yesterday when writing a docker compose I had found an issue realted to SQL Server and macbooks running ARM processors (M1 and the likes). I was writing this docker compose file for my customer's project that needs to use a SQL Server as their database. 
I work using a macbook pro m1 since the middle of 2021, and never got to try using SQL Server as my main database.

The issue is that the main docker containers for SQL Server doesn't have an ARM build, and using Rosetta emulation doesn't always works within their image... 

So, another way is to use the image: [`mcr.microsoft.com/azure-sql-edge:latest`](https://hub.docker.com/r/microsoft/azure-sql-edge). This image is a lightweight version of latest SQL Server based on Microsoft product [Azure SQL Edge](https://azure.microsoft.com/en-us/products/azure-sql/edge/), it's the version used for edge and IoT and is compatible with ARM processors!

Yay! 😊

This is my `docker-compose` file used for local development:

```yaml
version: '3.8'

services:
  sqlserver:
    # compatible with mac arm architecture, lightweight sql server
    image: mcr.microsoft.com/azure-sql-edge:latest
    
    # this one is compatible with x86 architecture, not so much on arm, full fledged sql server
    #image: mcr.microsoft.com/mssql/server:latest 

    container_name: sqlserver
    restart: always
    cap_add: [ 'SYS_PTRACE' ]
    ports:
      - "1433:1433"
    environment:
      ACCEPT_EULA: "Y"
      MSSQL_SA_PASSWORD: "IndeedVeryStrongPassword!"
      MSSQL_PID: "Developer"
    volumes:
      - sql_data:/var/opt/mssql
  
volumes:
  sql_data:
```