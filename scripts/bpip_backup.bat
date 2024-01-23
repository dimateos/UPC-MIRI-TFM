@echo off
REM backup env (using some common external .bat)

set "openWith=NONE"
if not [%1]==[] set "openWith=%1"
::echo %openWith%

CALL ./env
CALL %getTS%

set "folder=_bpip_backs"
if not exist %folder% mkdir %folder%

set "back=./%folder%/%ts%.freeze"
%bpip% freeze > %back%

if not [%openWith%]==[NONE] %openWith% %back%