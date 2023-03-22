@echo off
REM mirror some data files to shared drive folder (no purge of old files)

set "src=..\DATA"
:: set "dest=C:\OneDrive\Drive Google\UPC\_TFM\DATA"

REM shared folder direclty (hased path tho)
set "dest=C:\Users\Diego\Desktop\__stream-DRIVE\UPC\.shortcut-targets-by-id\1y_ROJTEoZxvMw6SsSFvZTUuMaTztJfSi\TFM Diego Mateos\DATA"

set "folder=Blender"
set "build=3.4.1"

pushd %cd%
:build
    CALL ./_scripts/getTS.bat
    REM zip locally before moving to drive (move is slash sensitive)

    cd %src%\%folder%
    set "tmp=%build%-20230322104245.zip"
    set "tmp_dest=%dest%\%folder%\%build%-20230322104245.zip"

    REM maybe also ignore _vendor and _distools?
    echo Zipping (will take over a minute)... output may be redirected to avoid flooding!
    zip -r %tmp% ./%build% -x "*/__pycache__/*"

    if not exist "%dest%/%folder%" mkdir "%dest%/%folder%"
    move "%tmp%" "%tmp_dest%"

popd
