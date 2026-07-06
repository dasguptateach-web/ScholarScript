$projectDir = "C:\Users\81\AppData\Local\Temp\opencode\scholarscript"
Set-Location $projectDir

# Fix Python stdlib path warning
$env:PYTHONHOME = "C:\Users\81\AppData\Local\Programs\Python\Python311"

if (-not (Test-Path "$projectDir\public\index.html")) {
    Write-Host "Building site first..." -ForegroundColor Yellow
    python -m scholarscript build 2>&1 | Out-Null
}

Write-Host "Starting ScholarScript preview at http://localhost:8000" -ForegroundColor Green
Start-Process "http://localhost:8000"
python -m http.server 8000 -d "$projectDir\public"