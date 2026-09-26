@echo off
REM ScholarScript Auto-Pipeline Launcher
REM Double-click this to start the full auto pipeline
cd /d "%~dp0"
start powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%~dp0watcher-supervisor.ps1"
echo ScholarScript Auto-Pipeline started in background window.
echo.
echo Drop .docx, .pdf, .txt files into the "ScholarScript Drop" folder on your Desktop.
echo The pipeline will: Ingest ^> YouTube Match ^> Build ^> Deploy
pause
