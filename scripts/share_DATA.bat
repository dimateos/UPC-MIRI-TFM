@echo off
REM mirror some data files to shared drive folder (no purge of old files)

set "src=..\DATA"
:: set "dest=C:\OneDrive\Drive Google\UPC\_TFM\DATA"

REM shared folder direclty (hased path tho)
set "dest=C:\Users\Diego\Desktop\__stream-DRIVE\UPC\.shortcut-targets-by-id\1y_ROJTEoZxvMw6SsSFvZTUuMaTztJfSi\TFM Diego Mateos\DATA"

:assets
    set "folder=models-TEST"
    robocopy "%src%/%folder%" "%dest%/%folder%" *.blend /MIR /FFT /MT:32 /R:1 /W:1 &REM limit to non backup files

    :: set "folder=models-Terrenos"
    :: robocopy "%src%/%folder%" "%dest%/%folder%" /MIR /FFT /MT:32 /R:1 /W:1

    :: set "folder=geogebra"
    :: robocopy "%src%/%folder%" "%dest%/%folder%" /MIR /FFT /MT:32 /R:1 /W:1

:src
    set "folder=py_object_fracture_cell"
    robocopy "%src%/%folder%" "%dest%/%folder%" /MIR /FFT /MT:32 /R:1 /W:1