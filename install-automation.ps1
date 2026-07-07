# ScholarScript Full Automation Installer v2.0
# Sets up 100% zero-touch pipeline: Drop file -> Ingest -> YouTube -> Build -> Deploy
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$taskName = "ScholarScript Auto-Pipeline"
$desktop = [Environment]::GetFolderPath("Desktop")
$dropFolder = "$desktop\ScholarScript Drop"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " ScholarScript Auto-Pipeline Installer v2" -ForegroundColor Cyan
Write-Host " Zero-touch: drop -> ingest -> YouTube ->" -ForegroundColor Cyan
Write-Host "                      build -> deploy" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# 0. Prerequisites
Write-Host "[0/6] Installing prerequisites..." -ForegroundColor Yellow
try { pip install yt-dlp -q 2>$null; Write-Host "  [OK] yt-dlp installed" -ForegroundColor Green }
catch { Write-Host "  [WARN] yt-dlp install issue: $_" -ForegroundColor Yellow }

if (-not (Test-Path $dropFolder)) { New-Item -ItemType Directory -Path $dropFolder -Force | Out-Null }
Write-Host "  [OK] Drop folder: $dropFolder" -ForegroundColor Green

foreach ($d in @("$dropFolder\_staging", "$dropFolder\_Processed")) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
}

# 1. Scheduled Task - auto-start at login
Write-Host "[1/6] Creating scheduled task (auto-start at login)..." -ForegroundColor Yellow
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File ""$projectDir\desktop-drop.ps1"""
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -Hidden
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -RunLevel Highest
try {
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
    Write-Host "  [OK] Task registered - runs silently at every login" -ForegroundColor Green
} catch { Write-Host "  [ERR] $($_.Exception.Message)" -ForegroundColor Red }

# 2. Desktop shortcut for manual start
Write-Host "[2/6] Creating desktop shortcut..." -ForegroundColor Yellow
$shortcutPath = "$desktop\Start ScholarScript Pipeline.lnk"
try {
    $wshell = New-Object -ComObject WScript.Shell
    $s = $wshell.CreateShortcut($shortcutPath)
    $s.TargetPath = "powershell.exe"
    $s.Arguments = "-ExecutionPolicy Bypass -WindowStyle Hidden -File ""$projectDir\desktop-drop.ps1"""
    $s.WorkingDirectory = $projectDir
    $s.Description = "ScholarScript auto-pipeline: watches Desktop\ScholarScript Drop"
    $s.Save()
    Write-Host "  [OK] Shortcut created" -ForegroundColor Green
} catch { Write-Host "  [ERR] $($_.Exception.Message)" -ForegroundColor Red }

# 3. Drop folder shortcut
Write-Host "[3/6] Creating drop-folder shortcut..." -ForegroundColor Yellow
$dropShortcut = "$desktop\Open Drop Folder.lnk"
try {
    $s = $wshell.CreateShortcut($dropShortcut)
    $s.TargetPath = "explorer.exe"
    $s.Arguments = $dropFolder
    $s.Description = "Drag files here to auto-publish"
    $s.Save()
    Write-Host "  [OK] Drop folder shortcut on Desktop" -ForegroundColor Green
} catch { Write-Host "  [ERR] $($_.Exception.Message)" -ForegroundColor Red }

# 4. Install ScholarScript
Write-Host "[4/6] Ensuring ScholarScript is installed..." -ForegroundColor Yellow
try {
    $installed = pip show scholarscript 2>$null
    if (-not $installed) { pip install -e "$projectDir" -q }
    Write-Host "  [OK] ScholarScript ready" -ForegroundColor Green
} catch { Write-Host "  [ERR] $($_.Exception.Message)" -ForegroundColor Red }

# 5. Ensure desktop-drop.bat launcher
Write-Host "[5/6] Updating launcher..." -ForegroundColor Yellow
$batPath = "$projectDir\desktop-drop.bat"
@"
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
"@ | Set-Content -Path $batPath -Force

# 6. Start the watcher now
Write-Host "[6/6] Starting watcher NOW..." -ForegroundColor Yellow
try {
    $proc = Start-Process powershell.exe -ArgumentList "-ExecutionPolicy Bypass -WindowStyle Hidden -File ""$projectDir\desktop-drop.ps1""" -PassThru
    Write-Host "  [OK] Watcher started (PID: $($proc.Id)) - running silently" -ForegroundColor Green
} catch { Write-Host "  [ERR] $($_.Exception.Message)" -ForegroundColor Red }

Write-Host ""
Write-Host "==================================================" -ForegroundColor Green
Write-Host "            SETUP COMPLETE!                        " -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Drop any .pdf/.docx/.txt into:" -ForegroundColor White
Write-Host "    Desktop\ScholarScript Drop\" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Pipeline runs FULLY AUTOMATICALLY:" -ForegroundColor White
Write-Host "    1. Ingest paper" -ForegroundColor Gray
Write-Host "    2. Find YouTube video" -ForegroundColor Gray
Write-Host "    3. Build site" -ForegroundColor Gray
Write-Host "    4. Deploy to website" -ForegroundColor Gray
Write-Host ""
Write-Host "  No manual steps needed ever." -ForegroundColor Green
Write-Host "  Watcher auto-starts at every login." -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to close"
