@echo off
REM install/update my remote voro repo

:_env
    REM unsintall current version
    CALL ./update_voro none

:_install
    REM install explicitly to local python
    %bpip% install git+%dBUILD_remote% -t %bpackages%
