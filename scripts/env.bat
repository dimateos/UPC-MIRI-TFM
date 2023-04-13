@echo off
REM env variables for local python expanded to absolute path

REM use local blender python to be able to share the enviroment easily
CALL :getAbsPath "..\DATA\Blender\3.4.1\3.4\python\bin\python.exe"
set bpy=%RETVAL%
::echo SET bpy: %bpy%

REM pass arguments directly to local pip
set bpip=%bpy% -m pip

REM open blender
CALL :getAbsPath "..\DATA\Blender\3.4.1\blender.exe"
set bexe=%RETVAL%

REM path to shared stuff
set "src=..\DATA"
set "src_folder=Blender"
set "src_build=3.4.1"
set "dest=C:\Users\Diego\Desktop\__stream-DRIVE\UPC\.shortcut-targets-by-id\1y_ROJTEoZxvMw6SsSFvZTUuMaTztJfSi\TFM Diego Mateos\DATA"
::set "dest=C:\OneDrive\Drive Google\UPC\_TFM\DATA"


::========== FUNCTIONS ==========
EXIT /b

REM Return: Resolved absolute path in RETVAL.
:getAbsPath
    set RETVAL=%~f1
    EXIT /b