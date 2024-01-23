@echo off
REM env variables for local python expanded to absolute path

REM shared paths
:_paths
    set "dDATA=..\DATA"
    set "nBLENDER=Blender"
    set "dBLENDER=%dDATA%\%nBLENDER%"
    set "nBUILD=3.4.1"
    set "dBUILD=%dBLENDER%\%nBUILD%"

:_env:
    REM use local blender python to be able to share the enviroment easily
    CALL :getAbsPath "%dBUILD%\3.4\python\bin\python.exe"
    set bpy=%RETVAL%
    ::echo SET bpy: %bpy%

    REM pass arguments directly to local pip
    set bpip=%bpy% -m pip

    REM open blender
    CALL :getAbsPath "%dBUILD%\blender.exe"
    set bexe=%RETVAL%
    CALL :getAbsPath "%dBUILD%\3.4\scripts\addons"
    set bscripts=%RETVAL%
    CALL :getAbsPath "%dBUILD%\3.4\python\lib\site-packages"
    set bpackages=%RETVAL%

:_voro
    REM local voro repo
    set "dBUILD_tfm=%dDATA%\UPC-MIRI-TFM-tess"
    set "fBUILD_cfg=%dBUILD_tfm%\src\config.hh"
    set "fBUILD_dbins=%dBUILD_tfm%\build"
    set "fBUILD_pybin=%dBUILD_tfm%\tess\_voro.*.pyd"
    REM remote updated repo
    set "dBUILD_remote=https://github.com/dimateos/UPC-MIRI-TFM-tess"
    REM local original repo (could just install from remote tho)
    set "dBUILD_tess=%dDATA%\py_tess"

:_share
    REM path to shared stuff
    set "dSHARED=C:\Users\Diego\Desktop\__stream-DRIVE\UPC\.shortcut-targets-by-id\1y_ROJTEoZxvMw6SsSFvZTUuMaTztJfSi\TFM Diego Mateos"
    set "dSHARED_DATA=%dSHARED%\Blender"

:_scripts
    ::set "getTS=.\_scripts\getTS.bat"
    set "getTS=.\getTS.bat"

::========== FUNCTIONS ==========
EXIT /b

REM Return: Resolved absolute path in RETVAL.
:getAbsPath
    set RETVAL="%~f1" &REM add quotes for paths with spaces
    EXIT /b