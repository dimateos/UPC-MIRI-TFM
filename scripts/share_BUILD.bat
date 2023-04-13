@echo off
REM mirror some data files to shared drive src_folder (no purge of old files)
REM TODO: final version using a fresh blender install + minimal addons (no debug libs etc)

REM shared data and shared path
CALL ./env


pushd %cd%
:src_build
    CALL ./_scripts/getTS.bat
    REM zip locally before moving to drive (move is slash sensitive)

    cd %src%\%src_folder%
    set "tmp=%src_build%-%ts%.zip"
    set "tmp_dest=%dest%\%src_folder%\%src_build%-%ts%.zip"

    REM maybe also ignore _vendor and _distools?
    REM NOTE: I could also overwrite only the addon folder inside the zip instead of a whole version, or just update changed files
    echo Zipping (will take over a minute)... output may be redirected to avoid flooding!
    zip -r %tmp% ./%src_build% -x "*/__pycache__/*"

    REM more files can be added to the existing zip afterwards, but the addon symlink is copied correclty already
    ::zip -r %tmp% ./%src_build%/3.4/scripts/addons/_addon_vscode -x "*/__pycache__/*"

    if not exist "%dest%/%src_folder%" mkdir "%dest%/%src_folder%"
    move "%tmp%" "%tmp_dest%"

popd
