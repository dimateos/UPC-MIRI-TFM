@echo off
REM mirror some data files to shared drive dBLENDER (no purge of old files)
REM TODO: final version using a fresh blender install + minimal addons (no debug libs etc)

REM shared data and shared path
CALL ./env
:_check_shared
    if not exist "%dSHARED_DATA%" EXIT /B

pushd %cd%
:_zip
    CALL ./_scripts/getTS.bat
    REM zip locally before moving to drive (move is slash sensitive)

    cd %dBLENDER%
    set "zip_file=%nBUILD%-%ts%.zip"
    set "dest=%dSHARED_DATA%\%nBLENDER%"
    set "zip_dest=%dest%\%zip_file%"

    REM maybe also ignore _vendor and _distools?
    REM NOTE: I could also overwrite only the addon folder inside the zip instead of a whole version, or just update changed files
    echo Zipping (will take over a minute)... output may be redirected to avoid flooding!
    zip -r %zip_file% ./%nBUILD% -x "*/__pycache__/*"

    REM more files can be added to the existing zip afterwards, but the addon symlink is copied correclty already
    ::zip -r %zip_file% ./%nBUILD%/3.4/scripts/addons/_addon_vscode -x "*/__pycache__/*"

:_move
    if not exist "%dest%" mkdir "%dest%"
    ::move "%zip_file%" "%zip_dest%"

popd
