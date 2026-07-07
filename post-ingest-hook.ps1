# ScholarScript Post-Ingestion Hook — Auto YouTube + Build + Deploy
# Called by desktop-drop.ps1 after successful ingestion
param(
    [string]$ProjectDir = "",
    [switch]$SkipDeploy
)

if (-not $ProjectDir) { $ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path }
Set-Location $ProjectDir

$pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $pythonExe) { $pythonExe = "python" }

Write-Host "╔══════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   Post-Ingestion Pipeline v2.0       ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════╝" -ForegroundColor Cyan

# STEP 1: YouTube Auto-Match
Write-Host "`n[1/3] Matching YouTube videos for new papers..." -ForegroundColor Yellow
$r = & $pythonExe youtube_agent.py 2>&1 | Out-String
Write-Host $r

# STEP 2: Build
Write-Host "`n[2/3] Building static site..." -ForegroundColor Yellow
$r = & $pythonExe -m scholarscript build 2>&1 | Out-String
Write-Host $r

# STEP 3: Deploy
if (-not $SkipDeploy) {
    Write-Host "`n[3/3] Deploying to GitHub Pages..." -ForegroundColor Yellow
    $ts = Get-Date -Format "yyyyMMdd-HHmmss"
    git add -A 2>&1 | Out-Null
    git commit -m "Auto-pipeline $ts" --allow-empty 2>&1 | Out-Null
    $pushResult = git push origin main 2>&1 | Out-String
    Write-Host $pushResult
}

Write-Host "`nPipeline complete!" -ForegroundColor Green
