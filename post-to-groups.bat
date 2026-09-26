@echo off
REM ScholarScript Guided Group Poster
REM Opens each social group with the promo post ready in your clipboard -
REM you just Ctrl+V and click Post
cd /d "%~dp0"
powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%~dp0post-to-groups.ps1"
