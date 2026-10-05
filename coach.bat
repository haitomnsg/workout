@echo off
REM Your trainer -- one double-click. Opens the app in your browser.
REM Keep this window open while you train; close it to stop.
REM   coach                 normal
REM   coach --no-voice      silent
"%~dp0.venv\Scripts\python.exe" -m trainer.web %*
