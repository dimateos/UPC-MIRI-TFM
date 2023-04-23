@echo off
REM backup and update bpip

CALL ./env
CALL ./_scripts/getTS.bat
CALL ./bpip_backup.bat

%bpip% install --upgrade pip