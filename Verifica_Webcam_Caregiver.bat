@echo off
title SteadyMotion AI - Verifica Hardware e Webcam Caregiver
color 0B
echo ========================================================
echo   STEADYMOTION AI v3.0 - DIAGNOSTICA WEBCAM & HARDWARE
echo ========================================================
echo.
echo Avvio del controllo automatico sensori...
echo.

python diagnostica_hardware.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ATTENZIONE: Errore durante l'esecuzione della diagnostica Python.
    echo Verificare che Python sia installato o eseguire da ambiente SteadyMotion.
    pause
)
