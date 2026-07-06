$projectDir = "C:\Users\81\ScholarScript"
$taskName = "ScholarScript Watcher"

Write-Host "ScholarScript Automation Setup" -ForegroundColor Cyan
Write-Host "==============================" -ForegroundColor Cyan
Write-Host ""

# 1. Create Scheduled Task for watcher auto-start at login
Write-Host "[1/4] Creating scheduled task..." -ForegroundColor Yellow
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File ""$projectDir\desktop-drop.ps1"""
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -RunLevel Highest

try {
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
    Write-Host "  [OK] Task '$taskName' created - runs at logon" -ForegroundColor Green
} catch {
    Write-Host "  [ERR] Failed to create task: $_" -ForegroundColor Red
}

# 2. Create Desktop shortcut for manual start
Write-Host "[2/4] Creating desktop shortcut..." -ForegroundColor Yellow
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = "$desktop\ScholarScript Watcher.lnk"
try {
    $wshell = New-Object -ComObject WScript.Shell
    $shortcut = $wshell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = "powershell.exe"
    $shortcut.Arguments = "-ExecutionPolicy Bypass -WindowStyle Hidden -File ""$projectDir\desktop-drop.ps1"""
    $shortcut.WorkingDirectory = $projectDir
    $shortcut.Description = "ScholarScript auto-upload watcher"
    $shortcut.Save()
    Write-Host "  [OK] Desktop shortcut created" -ForegroundColor Green
} catch {
    Write-Host "  [ERR] Failed to create shortcut: $_" -ForegroundColor Red
}

# 3. Update Upload to ScholarScript.bat
Write-Host "[3/4] Updating Upload shortcut..." -ForegroundColor Yellow
$uploadBat = "$desktop\Upload to ScholarScript.bat"
if (Test-Path $uploadBat) {
    try {
        Set-Content -Path $uploadBat -Value "@echo off`npowershell -ExecutionPolicy Bypass -File ""$projectDir\quick-upload.ps1"" -Paths %*" -Force
        Write-Host "  [OK] Upload shortcut updated" -ForegroundColor Green
    } catch {
        Write-Host "  [ERR] Failed to update upload shortcut: $_" -ForegroundColor Red
    }
}

# 4. Start the watcher now
Write-Host "[4/4] Starting watcher..." -ForegroundColor Yellow
try {
    $proc = Start-Process powershell.exe -ArgumentList "-ExecutionPolicy Bypass -WindowStyle Hidden -File ""$projectDir\desktop-drop.ps1""" -PassThru -WindowStyle Hidden
    Write-Host "  [OK] Watcher started (PID: $($proc.Id))" -ForegroundColor Green
} catch {
    Write-Host "  [ERR] Failed to start watcher: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "==============================" -ForegroundColor Cyan
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host "  The watcher will auto-start" -ForegroundColor Green
Write-Host "  every time you log in." -ForegroundColor Green
Write-Host "==============================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Drop PDF/DOC/TXT files into:" -ForegroundColor White
Write-Host "  $env:USERPROFILE\Desktop\ScholarScript Drop" -ForegroundColor Yellow
Write-Host ""
Write-Host "Watcher log:" -ForegroundColor White
Write-Host "  $projectDir\desktop-drop.log" -ForegroundColor Yellow

Read-Host "Press Enter to close"
