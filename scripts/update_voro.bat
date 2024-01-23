@echo off
REM install/update voro in local development mode

REM arg to switch build: tfm(mine), tess(original), none(uninstall)
set "build=tfm"
if not [%1]==[] set "build=%1"
::echo %build%

:_env
    CALL ./env
    %bpy% --version

:_update
    REM own updated fork or local version
    %bpip% uninstall tess --yes

    REM force c++ module to be recompiled too...
    rd /S /Q %fBUILD_dbins%
    del /Q /F %fBUILD_pybin%

    if [%build%]==[tfm] (
        REM dynamic dev installation
        %bpip% install --editable %dBUILD_tfm%

    ) else if [%build%]==[tess] (
        REM install the original to test some changes
        %bpip% install --editable %dBUILD_tess%

    ) else if [%build%]==[none] (
        REM why not also just uninstalling
        echo just - UNINSTALLED -
    )

    REM other option but needs to be executed at the root of the library repository
    ::pushd %CD% && cd %dBUILD_tfm% && %bpy% setup.py develop && popd
