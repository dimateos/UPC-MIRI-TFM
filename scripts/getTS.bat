@echo off
REM composes a simple timestamp
REM TODO maybe move into f/ folder or somehting instead of root

set "join="
if not [%1]==[] set "join=%1"
set "sep="
if not [%2]==[] set "sep=%2"

set d=%DATE:~-4%%sep%%DATE:~3,2%%sep%%DATE:~0,2%
::echo %DATE%
::echo %d%

set t=%TIME:~0,2%%sep%%TIME:~3,2%%sep%%TIME:~6,2%
set t=%t: =0%
::echo %TIME%
::echo %t%

set ts=%d%%join%%t%
::echo %ts%

REM exit with succes code
EXIT /b 0