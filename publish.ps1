$projectDir = "C:\Users\81\AppData\Local\Temp\opencode\scholarscript"
$tokenFile = "$projectDir\.github_token"
$repoFile = "$projectDir\.github_repo"

Set-Location $projectDir

# First-time setup check
if (-not (Test-Path $tokenFile) -or -not (Test-Path $repoFile)) {
    Write-Host "First-time setup required." -ForegroundColor Yellow
    & "$projectDir\setup-github.ps1"
    exit
}

$env:GITHUB_TOKEN = (Get-Content $tokenFile -Raw).Trim()
$env:GITHUB_REPO = (Get-Content $repoFile -Raw).Trim()

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ScholarScript Publisher" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/3] Processing uploads..." -ForegroundColor Yellow
python -m scholarscript ingest 2>&1

Write-Host "[2/3] Building site..." -ForegroundColor Yellow
python -m scholarscript build 2>&1

Write-Host "[3/3] Deploying to $env:GITHUB_REPO ..." -ForegroundColor Yellow
python -m scholarscript deploy 2>&1

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Published!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

Read-Host "Press Enter to close"