@echo off
REM install or update dependencies, includes voro++

set "build=tfm"
if not [%1]==[] set "build=%1"
::echo %build%

:_env
    CALL ./env
    %bpy% --version

    if [%build%]==[none] goto _update

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
    REM own updated fork or local version
    %bpip% uninstall tess --yes
    ::%bpip% install ../DATA/UPC-MIRI-TFM-tess
    ::pushd %CD% && cd ../DATA/UPC-MIRI-TFM-tess && %bpy% setup.py develop && popd &REM needs to be executed at the root of the library repository

    if [%build%]==[tfm] (
        REM two methods of dynamic installation
        %bpip% install --editable ../DATA/UPC-MIRI-TFM-tess

    ) else if [%build%]==[tess] (
        REM install the original to test some changes
        %bpip% install --editable ../DATA/py_tess

    ) else if [%build%]==[none] (
        REM why not also just uninstalling
        echo just - UNINSTALLED -
    )

