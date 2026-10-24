@echo off
title SteadyMotion AI - Verifica Hardware e Webcam Caregiver
color 0B
echo ========================================================
echo   STEADYMOTION AI v3.0 - DIAGNOSTICA WEBCAM & HARDWARE
echo ========================================================
echo.
echo Avvio del controllo automatico sensori...
echo.

if exist "%~dp0SteadyMotion-AI.exe" (
    cd /d "%~dp0"
    "SteadyMotion-AI.exe" --diagnostics
) else if exist "%~dp0dist\SteadyMotion-AI\SteadyMotion-AI.exe" (
    cd /d "%~dp0dist\SteadyMotion-AI"
    "SteadyMotion-AI.exe" --diagnostics
) else (
    python "%~dp0diagnostica_hardware.py"
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ATTENZIONE: Errore durante l'esecuzione della diagnostica.
    pause
)
