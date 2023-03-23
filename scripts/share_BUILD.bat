@echo off
REM mirror some data files to shared drive folder (no purge of old files)
REM TODO: final version using a fresh blender install + minimal addons (no debug libs etc)

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
    set "tmp=%build%-%ts%.zip"
    set "tmp_dest=%dest%\%folder%\%build%-%ts%.zip"

    REM maybe also ignore _vendor and _distools?
    echo Zipping (will take over a minute)... output may be redirected to avoid flooding!
    zip -r %tmp% ./%build% -x "*/__pycache__/*"

    REM more files can be added to the existing zip afterwards, but the addon symlink is copied correclty already
    :: zip -r %tmp% ./%build%/3.4/scripts/addons/_addon_vscode -x "*/__pycache__/*"

    if not exist "%dest%/%folder%" mkdir "%dest%/%folder%"
    move "%tmp%" "%tmp_dest%"

popd
