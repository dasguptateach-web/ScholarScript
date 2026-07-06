$projectDir = "C:\Users\81\AppData\Local\Temp\opencode\scholarscript"
$uploadsDir = "$projectDir\uploads"
$desktopDrop = "$env:USERPROFILE\Desktop\ScholarScript Drop"
$stagingDir = "$desktopDrop\_staging"
$processedDir = "$desktopDrop\_Processed"
$logFile = "$projectDir\desktop-drop.log"
$lockFile = "$env:TEMP\scholarscript-drop.lock"

Set-Location $projectDir
$env:PYTHONHOME = "C:\Users\81\AppData\Local\Programs\Python\Python311"

$tokenFile = "$projectDir\.github_token"
if (Test-Path $tokenFile) { $env:GITHUB_TOKEN = (Get-Content $tokenFile -Raw).Trim() }

foreach ($d in @($uploadsDir, $desktopDrop, $stagingDir, $processedDir)) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
}

if (Test-Path $lockFile) {
    $pid2 = try { (Get-Content $lockFile -Raw).Trim() } catch { "" }
    $running = $pid2 -and (Get-Process -Id $pid2 -ErrorAction SilentlyContinue)
    if ($running) { exit }
}
$pid | Out-File $lockFile -Encoding utf8 -Force

function Log {
    param([string]$Msg)
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $Msg"
    try { Add-Content -Path $logFile -Value $line -ErrorAction Stop } catch {}
}

function Wait-FileReady {
    param([string]$Path, [int]$MaxWait = 15)
    for ($i = 0; $i -lt $MaxWait; $i++) {
        if (-not (Test-Path $Path)) { return $false }
        try {
            $size1 = (Get-Item $Path -ErrorAction Stop).Length
            Start-Sleep -Seconds 1
            $size2 = (Get-Item $Path -ErrorAction Stop).Length
            if ($size1 -eq $size2 -and $size1 -gt 0) {
                $s = [System.IO.File]::Open($Path, 'Open', 'Read', 'None')
                $s.Close()
                return $true
            }
        } catch { Start-Sleep -Seconds 1 }
    }
    return $false
}

function Safe-Copy {
    param([string]$Src, [string]$Dst)
    for ($i = 0; $i -lt 10; $i++) {
        try { Copy-Item -LiteralPath $Src -Destination $Dst -Force -ErrorAction Stop; return $true }
        catch { Start-Sleep -Seconds 1 }
    }
    return $false
}

function Safe-Move {
    param([string]$Src, [string]$Dst)
    for ($i = 0; $i -lt 10; $i++) {
        try { Move-Item -LiteralPath $Src -Destination $Dst -Force -ErrorAction Stop; return $true }
        catch { Start-Sleep -Seconds 1 }
    }
    return $false
}

function Run-WithTimeout {
    param([string]$Command, [int]$TimeoutSeconds)
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "powershell.exe"
    $psi.Arguments = "-ExecutionPolicy Bypass -NoProfile -Command $Command"
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true
    $psi.EnvironmentVariables["PYTHONHOME"] = $env:PYTHONHOME
    if ($env:GITHUB_TOKEN) { $psi.EnvironmentVariables["GITHUB_TOKEN"] = $env:GITHUB_TOKEN }
    $p = [System.Diagnostics.Process]::Start($psi)
    if ($p.WaitForExit($TimeoutSeconds * 1000)) {
        $out = $p.StandardOutput.ReadToEnd()
        $err = $p.StandardError.ReadToEnd()
        $lines = ($out + $err) -split "`n"
        return $lines, ($p.ExitCode -eq 0)
    }
    $p.Kill()
    return @("TIMEOUT after ${TimeoutSeconds}s"), $false
}

function Get-Timestamp { return Get-Date -Format "yyyyMMdd-HHmmss" }

function Process-Batch {
    $staged = @()
    Get-ChildItem -LiteralPath $desktopDrop -File | Where-Object { $_.Name -notmatch '^_' } | ForEach-Object {
        $f = $_.FullName
        $name = $_.Name
        $ext = [IO.Path]::GetExtension($name).ToLower()
        if ($ext -notin '.pdf','.doc','.docx','.txt','.tex','.odt','.rtf') {
            Safe-Move $f "$stagingDir\$name" | Out-Null
            Log "SKIP $name (unsupported)"
            return
        }
        if (Wait-FileReady $f) {
            if (Safe-Move $f "$stagingDir\$name") {
                Log "STAGE $name"
                $staged += "$stagingDir\$name"
            }
        } else {
            Log "TIMEOUT $name (still in use)"
        }
    }

    if ($staged.Count -eq 0) { return }

    foreach ($s in $staged) {
        $name = Split-Path $s -Leaf
        if (Safe-Copy $s "$uploadsDir\$name") {
            Log "COPY $name"
        }
    }

    $ok = $true
    Log "Ingesting..."
    $r, $ok = Run-WithTimeout "python -m scholarscript ingest 2>&1" 120
    if (-not $ok) { Log "  FAILED or TIMEOUT" }
    foreach ($l in $r) { Log "  $l" }

    if ($ok) {
        $ts = Get-Timestamp
        Log "Pushing to GitHub..."
        $r, $ok = Run-WithTimeout "git add -A; if (`$?) { git commit -m 'Auto-deploy $ts'; if (`$?) { git push origin main } } 2>&1" 120
        if ($ok) {
            Log "Pushed! Workflow will deploy."
        } else {
            $skip = $r | Where-Object { $_ -match 'nothing to commit' -or $_ -match 'Everything up-to-date' }
            if ($skip) {
                Log "  Nothing new to push"
                $ok = $true
            } else {
                Log "  PUSH FAILED"
                foreach ($l in $r) { Log "  $l" }
            }
        }
    }

    if ($ok) { Log "Done!" } else { Log "FAILED" }

    foreach ($s in $staged) {
        $name = Split-Path $s -Leaf
        Safe-Move $s "$processedDir\$name" | Out-Null
    }
    Log "Archived to _Processed"
}

Log "Watcher started"

while ($true) {
    $files = Get-ChildItem -LiteralPath $desktopDrop -File | Where-Object { $_.Name -notmatch '^_' }
    if ($files) { Process-Batch }
    Start-Sleep -Seconds 3
}
