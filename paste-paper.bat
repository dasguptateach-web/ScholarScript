@echo off
REM ScholarScript Paste-to-Publish Launcher
REM 1. Double-click this file
REM 2. A window opens - paste (Ctrl+V) your manuscript into it
REM 3. Click "Format & Publish" - everything else is automatic
cd /d "%~dp0"
powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%~dp0paste-paper.ps1"
