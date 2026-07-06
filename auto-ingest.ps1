$projectDir = "C:\Users\81\AppData\Local\Temp\opencode\scholarscript"
$uploadsDir = "$projectDir\uploads"

# Fix Python stdlib path warning
$env:PYTHONHOME = "C:\Users\81\AppData\Local\Programs\Python\Python311"

Write-Host "ScholarScript Auto-Ingest" -ForegroundColor Cyan
Write-Host "========================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Opening uploads folder for you to drop files..."
Start-Process explorer.exe $uploadsDir

Write-Host "2. Starting watch mode - files will be processed automatically as they arrive."
Write-Host "   (This window will stay open. Close it when you're done.)"
Write-Host ""
Set-Location $projectDir
Start-Process powershell.exe "-NoExit -Command Set-Location '$projectDir'; python -m scholarscript watch-uploads"
