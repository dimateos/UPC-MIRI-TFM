@echo off

REM using ./env works for multiple commands otherwise exits at the first
CALL ./env
:: %bpy% --version
:: %bpy% --version
:: %bpip% install --upgrade pip
:: %bpip% freeze

REM backup env (using some common external .bat)
CALL ./_scripts/getTS.bat
set "back=./logFreeze/%ts%.log"
%bpip% freeze > %back%

REM autocomplete for bpy and bmesh etc
%bpip% install fake-bpy-module-3.4

REM voro++ interface for this python version...
%bpip% install wheel
%bpip% install setuptools-scm
%bpip% install setuptools

REM own updated fork or local version
%bpip% uninstall tess --yes
:: %bpip% install ../DATA/UPC-MIRI-TFM-tess
REM two methods of dynamic installation
%bpip% install --editable ../DATA/UPC-MIRI-TFM-tess
:: pushd %CD% && cd ../DATA/UPC-MIRI-TFM-tess && %bpy% setup.py develop && popd &REM needs to be executed at the root of the library repository