# ScholarScript Paste-to-Publish v1.0
# Copy your manuscript text to the clipboard, then run this script.
# Pipeline: Clipboard -> Clean & Format -> Fix Tables/MCQs -> Build -> Commit & Push
# GitHub Actions deploys the site automatically after the push.

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectDir

# Auto-detect Python
$pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $pythonExe) { $pythonExe = "C:\Python310\python.exe" }

$tokenFile = "$projectDir\.github_token"
if (Test-Path $tokenFile) { $env:GITHUB_TOKEN = (Get-Content $tokenFile -Raw).Trim() }

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ScholarScript Paste-to-Publish" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# -- 1. Read clipboard --
$clip = Get-Clipboard -Raw -ErrorAction SilentlyContinue
if (-not $clip -or -not $clip.Trim()) {
    Write-Host "[ERROR] Clipboard is empty. Copy your manuscript text, then run again." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}
$wordCount = ($clip.Trim() -split '\s+').Count
Write-Host "Clipboard loaded ($wordCount words)." -ForegroundColor DarkCyan

# -- 2. Save to temp UTF-8 file (stable encoding, survives clipboard changes) --
$tmp = Join-Path $env:TEMP ("scholarscript-paste-" + (Get-Date -Format 'yyyyMMdd-HHmmss') + ".txt")
[System.IO.File]::WriteAllText($tmp, $clip, (New-Object System.Text.UTF8Encoding($false)))

# -- 3. Paste -> clean & formatted Markdown --
Write-Host "[1/4] Formatting pasted manuscript..." -ForegroundColor Yellow
& $pythonExe -m scholarscript paste --file "$tmp"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Paste/format failed." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

# -- 4. Extra formatting passes (same as desktop drop pipeline) --
Write-Host "[2/4] Fixing tables & MCQ formatting..." -ForegroundColor Yellow
& $pythonExe fix_tables.py 2>&1 | Out-Null
& $pythonExe format_mcqs.py 2>&1 | Out-Null

# -- 5. Build --
Write-Host "[3/4] Building site..." -ForegroundColor Yellow
& $pythonExe -m scholarscript build
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Build failed." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

# -- 6. Commit & push (GitHub Actions auto-deploys on push to main) --
Write-Host "[4/4] Deploying to GitHub Pages..." -ForegroundColor Yellow
$ts = Get-Date -Format "yyyyMMdd-HHmmss"
if ($env:GITHUB_TOKEN) {
    git remote set-url origin "https://dasguptateach-web:$($env:GITHUB_TOKEN)@github.com/dasguptateach-web/ScholarScript.git" 2>&1 | Out-Null
}
git add -A 2>&1 | Out-Null
$out = git commit -m "Paste-publish $ts" 2>&1
if ($out -match 'nothing to commit|nothing changed') {
    Write-Host "Nothing new to push." -ForegroundColor Yellow
} else {
    $pushed = $false
    for ($attempt = 0; $attempt -lt 3 -and -not $pushed; $attempt++) {
        if ($attempt -gt 0) { Start-Sleep -Seconds 3; Write-Host "  Retry $($attempt+1)..." -ForegroundColor DarkYellow }
        try {
            git fetch origin 2>&1 | Out-Null
            git merge -X ours origin/main --no-edit 2>&1 | Out-Null
            $out = git push origin main 2>&1
            if ($LASTEXITCODE -eq 0) { $pushed = $true }
            elseif ($out -match 'Everything up-to-date') { $pushed = $true }
            elseif ($out -match 'rejected|non-fast-forward') {
                Write-Host "  Behind remote - pulling..." -ForegroundColor DarkYellow
                git pull --no-rebase origin main --no-edit 2>$null
            } else { Write-Host "  PUSH ERROR: $out" -ForegroundColor DarkYellow }
        } catch { Write-Host "  GIT EX: $_" -ForegroundColor DarkYellow }
    }
    if ($env:GITHUB_TOKEN) {
        git remote set-url origin "https://github.com/dasguptateach-web/ScholarScript.git" 2>&1 | Out-Null
    }
    if ($pushed) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "  Published!" -ForegroundColor Green
        Write-Host "  https://dasguptateach-web.github.io/ScholarScript/papers/" -ForegroundColor Green
        Write-Host "  (GitHub Pages updates in ~1-2 minutes)" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Push failed - check internet connection / .github_token." -ForegroundColor Red
    }
}

Remove-Item $tmp -ErrorAction SilentlyContinue
Read-Host "Press Enter to close"
