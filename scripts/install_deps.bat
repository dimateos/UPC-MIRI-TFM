@echo off
REM backup + install/update dependencies (includes voro++)

:_env
    CALL ./env
    %bpy% --version

    REM backup env freeze to a txt
    CALL ./bpip_backup

REM %bpackages% forces to be installed in the local folder, otehrwise pip could skip it
REM the bad thing is that this forces a reinstall instead of a skip when is already in the correct path

:_deps
    REM voro++ interface for this python version...
    %bpip% install wheel -t %bpackages%
    %bpip% install setuptools-scm -t %bpackages%
    %bpip% install setuptools -t %bpackages%

    REM used for tests in the other repo
    %bpip% install pytest -t %bpackages%

    REM autocomplete for bpy and bmesh etc
    %bpip% install fake-bpy-module-3.4 -t %bpackages%

:_deps_dev
    REM TODO: maybe also install ipykernel?


REM update install the last version of the local tess package
:_update
    CALL ./update
