# ScholarScript Auto-Pipeline v2.0
# Drop any document on your Desktop → auto-ingest → YouTube match → build → deploy
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$uploadsDir = "$projectDir\uploads"
$desktopDrop = "$env:USERPROFILE\Desktop\ScholarScript Drop"
$stagingDir = "$desktopDrop\_staging"
$processedDir = "$desktopDrop\_Processed"
$mediaDir = "$projectDir\themes\classic\media"
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
    $psi.EnvironmentVariables["PATH"] = [Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [Environment]::GetEnvironmentVariable("PATH", "User")
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
    $hasMedia = $false
    $mediaExts = '.jpg','.jpeg','.png','.gif','.webp','.svg','.bmp','.mp4','.mov','.webm','.mkv','.avi','.mpg','.mpeg','.m4v','.mp3','.wav','.aac','.flac'
    Get-ChildItem -LiteralPath $desktopDrop -File | Where-Object { $_.Name -notmatch '^_' } | ForEach-Object {
        $f = $_.FullName; $name = $_.Name
        $ext = [IO.Path]::GetExtension($name).ToLower()
        if ($ext -in $mediaExts) {
            if (Wait-FileReady $f) {
                if (-not (Test-Path $mediaDir)) { New-Item -ItemType Directory -Path $mediaDir -Force | Out-Null }
                if (Safe-Move $f "$mediaDir\$name") { Log "MEDIA $name -> themes\classic\media"; $allFileNames += $name; $hasMedia = $true }
            } else { Log "TIMEOUT $name (still in use)" }
            return
        }
        if ($ext -notin '.pdf','.doc','.docx','.txt','.tex','.odt','.rtf') {
            Safe-Move $f "$stagingDir\$name" | Out-Null; Log "SKIP $name (unsupported)"; return
        }
        if (Wait-FileReady $f) {
            if (Safe-Move $f "$stagingDir\$name") { Log "STAGE $name"; $staged += "$stagingDir\$name"; $allFileNames += $name }
        } else { Log "TIMEOUT $name (still in use)" }
    }
    if ($staged.Count -eq 0 -and -not $hasMedia) { return }

    foreach ($s in $staged) {
        $name = Split-Path $s -Leaf
        if (Safe-Copy $s "$uploadsDir\$name") { Log "COPY $name" }
    }

    # ── STEP 1: INGEST ──────────────────────────────────────
    $ok = $true
    Log "=== STEP 1/7: Ingesting documents ==="
    $r, $ok = Run-WithTimeout "& '$pythonExe' -m scholarscript ingest 2>&1" 120
    if (-not $ok) { Log "  INGEST FAILED or TIMEOUT" }
    foreach ($l in $r) { Log "  $l" }

    # ── STEP 2: FIX TABLES ──────────────────────────────────
    if ($ok) {
        Log "=== STEP 2/7: Fixing table formatting ==="
        $r, $tblOk = Run-WithTimeout "& '$pythonExe' fix_tables.py 2>&1" 30
        foreach ($l in $r) { Log "  $l" }
    }

    # ── STEP 3: FIX MCQ FORMATTING ──────────────────────────
    if ($ok) {
        Log "=== STEP 3/8: Formatting MCQs ==="
        $r, $mcqOk = Run-WithTimeout "& '$pythonExe' format_mcqs.py 2>&1" 30
        foreach ($l in $r) { Log "  $l" }
    }

    # ── STEP 4: BUILD INTERACTIVE TESTS ─────────────────────
    if ($ok) {
        Log "=== STEP 4/8: Building interactive tests ==="
        $r, $testOk = Run-WithTimeout "& '$pythonExe' -m scholarscript.test_parser 2>&1" 30
        foreach ($l in $r) { Log "  $l" }
    }

    # ── STEP 5: YOUTUBE MATCH ───────────────────────────────
    if ($ok) {
        Log "=== STEP 5/8: Matching YouTube videos ==="
        $r, $ytOk = Run-WithTimeout "& '$pythonExe' youtube_agent.py 2>&1" 180
        foreach ($l in $r) { Log "  $l" }
        if (-not $ytOk) { Log "  YouTube step had issues (non-fatal, continuing)" }
    }

    # ── STEP 6: BUILD ───────────────────────────────────────
    if ($ok) {
        Log "=== STEP 6/8: Building site ==="
        $r, $ok = Run-WithTimeout "& '$pythonExe' -m scholarscript build 2>&1" 60
        if (-not $ok) { Log "  BUILD FAILED" }
        foreach ($l in $r) { Log "  $l" }
    }

    # ── STEP 7: COMMIT & PUSH ───────────────────────────────
    if ($ok) {
        $ts = Get-Timestamp; $pushed = $false
        Log "=== STEP 7/8: Committing and pushing to GitHub ==="
        
        # Configure git auth for scripted use
        if (Test-Path $tokenFile) { $env:GITHUB_TOKEN = (Get-Content $tokenFile -Raw).Trim() }
        if ($env:GITHUB_TOKEN) {
            $repoUrl = "https://dasguptateach-web:$env:GITHUB_TOKEN@github.com/dasguptateach-web/ScholarScript.git"
            git remote set-url origin $repoUrl 2>&1 | Out-Null
        }
        
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
                    } else { Log "  PUSH ERROR: $out" }
                }
            } catch { Log "  GIT EX: $_" }
        }
        
        # Restore original remote URL
        git remote set-url origin "https://github.com/dasguptateach-web/ScholarScript.git" 2>&1 | Out-Null
        
        if (-not $pushed) { $ok = $false }
    }

    # ── STEP 8: FINALIZE ────────────────────────────────────
    if ($ok) {
        Log "=== STEP 8/8: Done! ==="
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
