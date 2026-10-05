@echo off
REM Convenience launcher so you never have to think about the venv.
REM   workout squat 8
REM   workout bench 6
REM   workout row 7
REM Extra flags pass straight through, e.g.  workout squat 8 --sets 4 --reps 8

setlocal
set EXERCISE=%1
set WEIGHT=%2
if "%EXERCISE%"=="" set EXERCISE=squat

if "%WEIGHT%"=="" (
    "%~dp0.venv\Scripts\python.exe" -m trainer.main --exercise %EXERCISE%
) else (
    shift
    shift
    "%~dp0.venv\Scripts\python.exe" -m trainer.main --exercise %EXERCISE% --weight %WEIGHT% %1 %2 %3 %4 %5 %6
)
endlocal
