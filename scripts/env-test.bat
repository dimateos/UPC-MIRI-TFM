@echo off

REM using ./env works for multiple commands otherwise exits at the first
@REM call ./env
@REM %bpy% --version
@REM %bpy% --version

REM check packages to it
bpy --version
bpip freeze
bpy -c "help(\"modules\")"

REM autocomplete for bpy and bmesh etc
bpip install fake-bpy-module-3.4