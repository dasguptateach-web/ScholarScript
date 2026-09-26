# ScholarScript Watcher Supervisor - keeps the pipeline running 24x7
# Robust: uses PID files for detection; launches watcher shell-detached
$projectDir = "D:\ScholarScript"
$watcher = "$projectDir\desktop-drop.ps1"
$logFile = "$projectDir\desktop-drop.log"
$lockFile = "$env:TEMP\scholarscript-drop.lock"
$supPidFile = "$projectDir\supervisor.pid"

function Log {
    param([string]$Msg)
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] [SUPERVISOR] $Msg"
    try { Add-Content -Path $logFile -Value $line -ErrorAction Stop } catch {}
}

# Single-instance guard for the supervisor itself
if (Test-Path $supPidFile) {
    $existing = (Get-Content $supPidFile -Raw).Trim()
    if ($existing -match '^\d+$') {
        $ep = Get-Process -Id $existing -ErrorAction SilentlyContinue
        if ($ep -and $ep.Id -ne $PID) { exit }
    }
}
$PID | Out-File $supPidFile -Encoding utf8 -Force

Log "Supervisor started (PID $PID) - keeping watcher alive 24x7"

while ($true) {
    $watcherAlive = $false
    if (Test-Path $lockFile) {
        $wPid = (Get-Content $lockFile -Raw).Trim()
        if ($wPid -match '^\d+$') {
            $wp = Get-Process -Id $wPid -ErrorAction SilentlyContinue
            if ($wp) { $watcherAlive = $true }
        }
    }

    if (-not $watcherAlive) {
        Remove-Item $lockFile -Force -ErrorAction SilentlyContinue
        Log "Watcher not running - launching detached..."
        # Shell-launched (explorer-style) so it never inherits our console handles
        if (Test-Path "$projectDir\Start Watcher.lnk") {
            Start-Process "$projectDir\Start Watcher.lnk"
            Log "Launched via Start Watcher.lnk"
        } else {
            $psi = New-Object System.Diagnostics.ProcessStartInfo
            $psi.FileName = "cmd.exe"
            $psi.Arguments = "/c start `"`" /b powershell.exe -ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -File `"$watcher`""
            $psi.UseShellExecute = $false
            $psi.CreateNoWindow = $true
            $psi.RedirectStandardOutput = $true
            $psi.RedirectStandardError = $true
            [void][System.Diagnostics.Process]::Start($psi)
            Log "Launched via cmd start (large)"
        }
        Start-Sleep -Seconds 12

        # Verify by reading the lock PID the watcher should have written
        if (Test-Path $lockFile) {
            $wPid = (Get-Content $lockFile -Raw).Trim()
            if ($wPid -match '^\d+$') {
                $wp = Get-Process -Id $wPid -ErrorAction SilentlyContinue
                if ($wp) { Log "Watcher confirmed up (PID $($wp.Id))" }
            }
        } else {
            Log "Lock not written - will retry in 30s"
        }
    }
    Start-Sleep -Seconds 30
}