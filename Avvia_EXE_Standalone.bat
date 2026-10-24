@echo off
title SteadyMotion AI v3.0 - Standalone Executable Launcher
if exist "%~dp0SteadyMotion-AI.exe" (
    cd /d "%~dp0"
    start "" "SteadyMotion-AI.exe"
) else if exist "%~dp0dist\SteadyMotion-AI\SteadyMotion-AI.exe" (
    cd /d "%~dp0dist\SteadyMotion-AI"
    start "" "SteadyMotion-AI.exe"
) else (
    echo ERRORE: SteadyMotion-AI.exe non trovato!
    pause
)
exit
