@echo off
title ScholarScript Auto-Pipeline
cd /d "%~dp0"
echo Starting ScholarScript Auto-Pipeline...
echo.
echo Pipeline: Ingest -> YouTube Match -> Build -> Deploy
echo Drop files into: %USERPROFILE%\Desktop\ScholarScript Drop
echo.
start /B powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0desktop-drop.ps1"
echo Pipeline started!
timeout /t 3 /nobreak >nul
