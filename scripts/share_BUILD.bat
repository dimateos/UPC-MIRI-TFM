@echo off
REM mirror some data files to shared drive folder (no purge of old files)

set "local=..\DATA"
set "target=C:\OneDrive\Drive Google\UPC\_TFM\DATA"

set "folder=Blender"
set "build=3.4.1"

pushd %cd%
:build
    CALL ./_scripts/getTS.bat
    REM zip locally before moving to drive (move is slash sensitive)

    cd %local%\%folder%
    set "tmp=%build%-20230322104245.zip"
    set "tmp_target=%target%\%folder%\%build%-20230322104245.zip"

    REM maybe also ignore _vendor and _distools?
    echo Zipping (will take over a minute)... output may be redirected to avoid flooding!
    zip -r %tmp% ./%build% -x "*/__pycache__/*"

    if not exist "%target%/%folder%" mkdir "%target%/%folder%"
    move "%tmp%" "%tmp_target%"

popd
