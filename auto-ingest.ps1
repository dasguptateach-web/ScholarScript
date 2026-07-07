# ScholarScript Auto-Pipeline — Quick Start
# Opens uploads folder + watch mode + YouTube auto-match
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$uploadsDir = "$projectDir\uploads"

$env:PYTHONHOME = try { (Get-Command python).Source | Split-Path -Parent } catch { $env:LOCALAPPDATA + "\Programs\Python\Python313" }

Write-Host "╔══════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     ScholarScript Auto-Pipeline v2.0           ║" -ForegroundColor Cyan
Write-Host "║  Drop files → Ingest → YouTube → Build → Push  ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Step 1: Open uploads folder
Write-Host "[1/3] Opening uploads folder..." -ForegroundColor Yellow
Start-Process explorer.exe $uploadsDir

# Step 2: Install yt-dlp if needed
Write-Host "[2/3] Ensuring yt-dlp is installed..." -ForegroundColor Yellow
try { & python -m pip install yt-dlp -q | Out-Null } catch {}

# Step 3: Start the full auto-pipeline
Write-Host "[3/3] Starting auto-pipeline (ingest + YouTube + build + deploy)..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Drop .docx/.pdf/.txt files into: $uploadsDir" -ForegroundColor Green
Write-Host "The pipeline will auto-process them." -ForegroundColor Green
Write-Host "Close this window to stop." -ForegroundColor DarkGray

Set-Location $projectDir
Start-Process powershell.exe "-NoExit -Command Set-Location '$projectDir'; while(`$true) { `$files = Get-ChildItem '$uploadsDir' -File; if (`$files) { Write-Host '`n=== Processing files ===' -ForegroundColor Cyan; & python -m scholarscript ingest; & python youtube_agent.py; `$newPapers = Get-ChildItem 'content/papers' -File | Where-Object { `$_.LastWriteTime -gt (Get-Date).AddMinutes(-1) }; if (`$newPapers) { & python -m scholarscript build; `$ts = Get-Date -Format 'yyyyMMdd-HHmmss'; git add -A; git commit -m `"Auto-pipeline `$ts`" --allow-empty; git push origin main } } Start-Sleep -Seconds 10 }"
