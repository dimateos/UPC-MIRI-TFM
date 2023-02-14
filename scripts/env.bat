@echo off

REM use local blender python to be able to share the enviroment easily
set bpy="..\DATA\Blender\3.4.1\3.4\python\bin\python.exe"

REM pass arguments directly to local pip
set bpip=%bpy% -m pip