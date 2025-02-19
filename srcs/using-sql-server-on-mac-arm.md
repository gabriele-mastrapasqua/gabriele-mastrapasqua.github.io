---
title: Using SQL Server on my Mac M1
date: 2025-02-13
description: Let's run a docker container for SQL Server development even on mac m1
---

Yesterday I was running in an issue: I was developing a docker compose file and for a customer where I need to use SQL Server as the database. 
I use a macbook pro m1 since the middle of 2021, and never got to use SQL Server as my main database locally.

The issue is that the main docker containers for SQL Server doesn't have an ARM build, and using Rosetta emulation doesn't always works within their image... 

So, another way is to use the image: `mcr.microsoft.com/azure-sql-edge:latest`! This image is a lightweight version of latest SQL Server and is compatible with ARM processors!

This is my `docker-compose` file used for local developemnt:

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