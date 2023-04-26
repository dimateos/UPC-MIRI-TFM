@echo off
REM backup + install/update dependencies (includes voro++)

:_env
    CALL ./env
    %bpy% --version

    REM backup env freeze to a txt
    CALL ./bpip_backup

:_deps
    REM voro++ interface for this python version...
    %bpip% install wheel
    %bpip% install setuptools-scm
    %bpip% install setuptools

    REM used for tests in the other repo
    %bpip% install pytest

    REM autocomplete for bpy and bmesh etc
    %bpip% install fake-bpy-module-3.4

    REM TODO: maybe also install ipykernel?

:_update
    CALL ./update
