@echo off
REM env variables for local python expanded to absolute path

REM use local blender python to be able to share the enviroment easily
CALL :getAbsPath "..\DATA\Blender\3.4.1\3.4\python\bin\python.exe"
set bpy=%RETVAL%
:: echo SET bpy: %bpy%

REM pass arguments directly to local pip
set bpip=%bpy% -m pip

CALL :getAbsPath "..\DATA\Blender\3.4.1\blender.exe"
set bexe=%RETVAL%

:: ========== FUNCTIONS ==========
EXIT /b

REM Return: Resolved absolute path in RETVAL.
:getAbsPath
    set RETVAL=%~f1
    EXIT /b