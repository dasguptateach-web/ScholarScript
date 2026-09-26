@echo off
REM ScholarScript Paste-to-Publish Launcher
REM 1. Copy your manuscript text (Ctrl+C from Word/PDF/webpage)
REM 2. Double-click this file - it formats, watermarks and deploys it
cd /d "%~dp0"
powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%~dp0paste-paper.ps1"
