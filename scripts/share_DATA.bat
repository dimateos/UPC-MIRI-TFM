@echo off
REM mirror some data files to shared drive folder (no purge of old files)

REM shared data and shared path
CALL ./env


:assets
    set "folder=models-TEST"
    REM limit to non backup files
    robocopy "%dDATA%/%folder%" "%dSHARED_DATA%/%folder%" *.blend /MIR /FFT /MT:32 /R:1 /W:1

    ::set "folder=models-Terrenos"
    ::robocopy "%dDATA%/%folder%" "%dSHARED_DATA%/%folder%" /MIR /FFT /MT:32 /R:1 /W:1

    ::set "folder=geogebra"
    ::robocopy "%dDATA%/%folder%" "%dSHARED_DATA%/%folder%" /MIR /FFT /MT:32 /R:1 /W:1

:dDATA
    ::set "folder=py_object_fracture_cell"
    ::robocopy "%dDATA%/%folder%" "%dSHARED_DATA%/%folder%" /MIR /FFT /MT:32 /R:1 /W:1