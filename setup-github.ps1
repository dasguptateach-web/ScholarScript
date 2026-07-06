$projectDir = "C:\Users\81\AppData\Local\Temp\opencode\scholarscript"
Set-Location $projectDir

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  ScholarScript GitHub Setup" -ForegroundColor Cyan
Write-Host "  One-time configuration for publishing" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "You need a GitHub token and a repository name." -ForegroundColor Yellow

# --- GitHub Token ---
$existingToken = $env:GITHUB_TOKEN
if (-not $existingToken -and (Test-Path ".github_token")) {
    $existingToken = Get-Content ".github_token" -Raw | ForEach-Object { $_.Trim() }
}

if ($existingToken) {
    Write-Host "Token already saved." -ForegroundColor Green
} else {
    Write-Host "1. Open this link in your browser:" -ForegroundColor Yellow
    Write-Host "   https://github.com/settings/tokens/new?description=ScholarScript&scopes=repo,workflow" -ForegroundColor White
    Start-Process "https://github.com/settings/tokens/new?description=ScholarScript&scopes=repo,workflow"
    Write-Host "2. Click 'Generate token', then copy it and paste below." -ForegroundColor Yellow
    Write-Host ""
    $token = Read-Host "Paste your GitHub token"
    if ($token) {
        $token | Out-File ".github_token" -Encoding utf8
        Write-Host "Token saved." -ForegroundColor Green
    } else {
        Write-Host "No token entered. You can run this setup again later." -ForegroundColor Red
    }
}

# --- GitHub Repo ---
$existingRepo = $env:GITHUB_REPO
if (-not $existingRepo -and (Test-Path ".github_repo")) {
    $existingRepo = Get-Content ".github_repo" -Raw | ForEach-Object { $_.Trim() }
}

if ($existingRepo) {
    Write-Host "Repo already saved: $existingRepo" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "3. Create a repository on GitHub:" -ForegroundColor Yellow
    Write-Host "   https://github.com/new" -ForegroundColor White
    Start-Process "https://github.com/new"
    Write-Host "4. Enter your repo name (just the name, e.g. 'ScholarScript'):" -ForegroundColor Yellow
    $repo = Read-Host "Repository name"
    if ($repo) {
        # Remove any accidental username/ prefix or leading slash
        $repo = $repo -replace '^.*/',''
        $repo = $repo -replace '^/',''
        $repo | Out-File ".github_repo" -Encoding utf8
        Write-Host "Repo saved: $repo (username auto-resolved at deploy time)" -ForegroundColor Green
    } else {
        Write-Host "No repo entered. You can run this setup again later." -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Setup complete! Now use the 'ScholarScript Publish' shortcut." -ForegroundColor Cyan
Read-Host "Press Enter to close"