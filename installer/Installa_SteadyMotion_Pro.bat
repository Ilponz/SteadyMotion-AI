@echo off
title Installatore SteadyMotion AI Pro (MDR SaMD Classe I)
setlocal

echo ==================================================================
echo   SteadyMotion AI - Installatore Clinico Pro
echo   Verifica Privilegi di Amministratore in corso...
echo ==================================================================

net session >nul 2>&1
if %errorLevel% == 0 (
    goto :run_install
) else (
    echo [RICHIESTA UAC] Elevazione privilegi richiesta per installazione in Program Files.
    powershell -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

:run_install
if exist "%~dp0Setup_Wizard.ps1" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Setup_Wizard.ps1"
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Create_Local_Cert_And_Install.ps1"
)

if %errorlevel% neq 0 (
    echo.
    echo [ERRORE] L'installazione ha restituito un codice di errore: %errorlevel%
    pause
    exit /b %errorlevel%
)
