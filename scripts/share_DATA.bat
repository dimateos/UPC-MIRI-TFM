@echo off
REM mirror some data files to shared drive folder (no purge of old files)

set "local=..\DATA"
set "target=C:\OneDrive\Drive Google\UPC\_TFM\DATA"

:assets
    set "folder=geogebra"
    robocopy "%local%/%folder%" "%target%/%folder%" /XO /MT:32 /R:1 /W:1

    set "folder=models-TEST"
    robocopy "%local%/%folder%" "%target%/%folder%" *.blend /XO /MT:32 /R:1 /W:1 &REM limit to non backup files

    set "folder=models-Terrenos"
    robocopy "%local%/%folder%" "%target%/%folder%" /XO /MT:32 /R:1 /W:1

:src
    set "folder=py_object_fracture_cell"
    robocopy "%local%/%folder%" "%target%/%folder%" /XO /MT:32 /R:1 /W:1