# ScholarScript Auto-Pipeline v2.0
# Drop any document on your Desktop → auto-ingest → YouTube match → build → deploy
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$uploadsDir = "$projectDir\uploads"
$desktopDrop = "$env:USERPROFILE\Desktop\ScholarScript Drop"
$stagingDir = "$desktopDrop\_staging"
$processedDir = "$desktopDrop\_Processed"
$logFile = "$projectDir\desktop-drop.log"
$lockFile = "$env:TEMP\scholarscript-drop.lock"

Set-Location $projectDir

# Auto-detect Python
$pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $pythonExe) { $pythonExe = "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe" }
if (-not $pythonExe) { $pythonExe = "C:\Python310\python.exe" }

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
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Msg"
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
    $psi.WorkingDirectory = $projectDir
    $psi.EnvironmentVariables["PATH"] = $env:PATH
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
    $allFileNames = @()
    $staged = @()
    Get-ChildItem -LiteralPath $desktopDrop -File | Where-Object { $_.Name -notmatch '^_' } | ForEach-Object {
        $f = $_.FullName; $name = $_.Name
        $ext = [IO.Path]::GetExtension($name).ToLower()
        if ($ext -notin '.pdf','.doc','.docx','.txt','.tex','.odt','.rtf') {
            Safe-Move $f "$stagingDir\$name" | Out-Null; Log "SKIP $name (unsupported)"; return
        }
        if (Wait-FileReady $f) {
            if (Safe-Move $f "$stagingDir\$name") { Log "STAGE $name"; $staged += "$stagingDir\$name"; $allFileNames += $name }
        } else { Log "TIMEOUT $name (still in use)" }
    }
    if ($staged.Count -eq 0) { return }

    foreach ($s in $staged) {
        $name = Split-Path $s -Leaf
        if (Safe-Copy $s "$uploadsDir\$name") { Log "COPY $name" }
    }

    # ── STEP 1: INGEST ──────────────────────────────────────
    $ok = $true
    Log "=== STEP 1/5: Ingesting documents ==="
    try {
        $ingestOut = & $pythonExe -m scholarscript ingest 2>&1
        foreach ($l in $ingestOut) { Log "  $l" }
        $ok = $LASTEXITCODE -eq 0
    } catch { Log "  INGEST EXCEPTION: $_"; $ok = $false }
    if (-not $ok) { Log "  INGEST FAILED" }

    # ── STEP 2: YOUTUBE MATCH ───────────────────────────────
    if ($ok) {
        Log "=== STEP 2/5: Matching YouTube videos ==="
        try {
            $ytOut = & $pythonExe "$projectDir\youtube_agent.py" 2>&1
            foreach ($l in $ytOut) { Log "  $l" }
        } catch { Log "  YouTube step error: $_" }
    }

    # ── STEP 3: BUILD ───────────────────────────────────────
    if ($ok) {
        Log "=== STEP 3/5: Building site ==="
        try {
            $buildOut = & $pythonExe -m scholarscript build 2>&1
            foreach ($l in $buildOut) { Log "  $l" }
            $ok = $LASTEXITCODE -eq 0
        } catch { Log "  BUILD EXCEPTION: $_"; $ok = $false }
        if (-not $ok) { Log "  BUILD FAILED" }
    }

    # ── STEP 4: COMMIT & PUSH ───────────────────────────────
    if ($ok) {
        $ts = Get-Timestamp; $pushed = $false
        Log "=== STEP 4/5: Committing and pushing to GitHub ==="
        try { git add -A 2>&1 | Out-Null } catch { Log "  ADD EX: $_" }
        try { $out = git commit -m "Auto-deploy $ts" 2>&1 } catch { Log "  COMMIT EX: $_" }
        if ($out -match 'nothing to commit|nothing changed') { Log "  Nothing new to push" }

        for ($attempt = 0; $attempt -lt 3 -and -not $pushed; $attempt++) {
            if ($attempt -gt 0) { Start-Sleep -Seconds 3; Log "  Retry $($attempt+1)..." }
            try {
                $out = git fetch origin 2>&1
                $out = git merge -X ours origin/main --no-edit 2>&1
                if ($LASTEXITCODE -ne 0) {
                    if ($out -match 'conflict|CONFLICT|merge failed') {
                        Log "  Conflict resolving..."; git merge --abort 2>$null
                        git merge -X theirs origin/main --no-edit 2>$null
                        if ($LASTEXITCODE -ne 0) { git merge --abort 2>$null }
                    }
                }
                $out = git push origin main 2>&1
                if ($LASTEXITCODE -eq 0) { Log "  Pushed!"; $pushed = $true }
                elseif ($out -match 'Everything up-to-date') { Log "  Up-to-date"; $pushed = $true }
                else {
                    if ($out -match 'rejected|non-fast-forward') {
                        Log "  Behind remote - pulling..."
                        git pull --no-rebase origin main --no-edit 2>$null
                    }
                }
            } catch { Log "  GIT EX: $_" }
        }
        if (-not $pushed) { $ok = $false }
    }

    # ── STEP 5: FINALIZE ────────────────────────────────────
    if ($ok) {
        Log "=== STEP 5/5: Done! ==="
        Log "Files: $($allFileNames -join ', ')"
    } else { Log "FAILED - check log above" }

    foreach ($s in $staged) {
        $name = Split-Path $s -Leaf
        Safe-Move $s "$processedDir\$name" | Out-Null
    }
    Log "Archived to _Processed"
}

Log "Auto-Pipeline v2.0 started (project: $projectDir)"

while ($true) {
    $files = Get-ChildItem -LiteralPath $desktopDrop -File | Where-Object { $_.Name -notmatch '^_' }
    if ($files) { Process-Batch }
    Start-Sleep -Seconds 3
}
