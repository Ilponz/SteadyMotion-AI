@echo off
title SteadyMotion AI - Assistive Head Tracker
cd /d "%~dp0"
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Si e' verificato un errore durante l'esecuzione di SteadyMotion AI.
    pause
)
