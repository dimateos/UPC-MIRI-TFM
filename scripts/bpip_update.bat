@echo off
REM backup and update bpip

CALL ./env
CALL %getTS%
CALL ./bpip_backup.bat

%bpip% install --upgrade pip