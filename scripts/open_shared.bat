@echo off
CALL ./env
:_check_shared
    if not exist "%dSHARED_DATA%" EXIT /B

explorer "%dSHARED_DATA%"
