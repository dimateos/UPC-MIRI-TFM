@echo off

REM using ./env works for multiple commands otherwise exits at the first
@REM call ./env
@REM %bpy% --version
@REM %bpy% --version

REM check packages to it
bpy --version
bpy -c "help(\"modules\")"
bpip freeze

REM backup env (using some common external .bat)
call ./_ext/getTS.bat
set "back=./logFreeze/%ts%.log"
bpip freeze > %back%

REM autocomplete for bpy and bmesh etc
bpip install fake-bpy-module-3.4

REM voro++ interface for this python version...
bpip install wheel
bpip install setuptools-scm
bpip install setuptools

REM all fail when compiling c++ interface... 'Python.h': No such file or directory
bpip install tess
bpip install git+https://github.com/eleftherioszisis/tess
bpip install git+https://github.com/joe-jordan/pyvoro@feature/python3

REM updated fork
bpip install --force-reinstall git+https://github.com/dimateos/UPC-MIRI-TFM-tess
bpip install --upgrade git+https://github.com/dimateos/UPC-MIRI-TFM-tess