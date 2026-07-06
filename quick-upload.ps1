param(
    [string[]]$Paths
)

$projectDir = "C:\Users\81\AppData\Local\Temp\opencode\scholarscript"
$uploadsDir = "$projectDir\uploads"

Set-Location $projectDir

# Fix Python stdlib path warning
$env:PYTHONHOME = "C:\Users\81\AppData\Local\Programs\Python\Python311"

function Show-FilePicker {
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = New-Object System.Windows.Forms.OpenFileDialog
    $dialog.Multiselect = $true
    $dialog.Filter = "Documents (*.pdf,*.doc,*.docx,*.txt,*.tex,*.odt,*.rtf)|*.pdf;*.doc;*.docx;*.txt;*.tex;*.odt;*.rtf"
    $dialog.Title = "Select files to upload to ScholarScript"
    $result = $dialog.ShowDialog()
    if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
        return $dialog.FileNames
    }
    return $null
}

function Copy-Files {
    param([string[]]$Files)
    $copied = @()
    foreach ($f in $Files) {
        if (Test-Path $f) {
            $ext = [System.IO.Path]::GetExtension($f).ToLower()
            if ($ext -in '.pdf','.doc','.docx','.txt','.tex','.odt','.rtf') {
                Copy-Item -LiteralPath $f -Destination $uploadsDir -Force
                $copied += $f
                Write-Host "  [OK] $(Split-Path $f -Leaf)" -ForegroundColor Green
            } else {
                Write-Host "  [SKIP] $(Split-Path $f -Leaf) - unsupported format (use PDF, DOC, DOCX, TXT, TEX, ODT, RTF)" -ForegroundColor Yellow
            }
        }
    }
    return $copied
}

Clear-Host
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  ScholarScript Quick Upload" -ForegroundColor Cyan
Write-Host "  Drag & drop files onto this window" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Get files
if ($Paths.Count -eq 0 -or [string]::IsNullOrWhiteSpace($Paths[0])) {
    Write-Host "Opening file picker..." -ForegroundColor Yellow
    $selected = Show-FilePicker
    if (-not $selected) {
        Write-Host "No files selected. Exiting." -ForegroundColor Red
        Read-Host "Press Enter to close"
        exit
    }
    $Paths = $selected
}

# Step 1: Copy files
Write-Host "[1/4] Copying files to uploads folder..." -ForegroundColor Yellow
if (-not (Test-Path $uploadsDir)) {
    New-Item -ItemType Directory -Path $uploadsDir -Force | Out-Null
}
$copied = Copy-Files -Files $Paths
if ($copied.Count -eq 0) {
    Write-Host "No valid files to process. Exiting." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit
}
Write-Host "    Copied $($copied.Count) file(s)" -ForegroundColor Green
Write-Host ""

# Step 2: Ingest
Write-Host "[2/4] Ingesting documents..." -ForegroundColor Yellow
python -m scholarscript ingest 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Ingestion failed. Check errors above." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit
}
Write-Host ""

# Step 3: Build
Write-Host "[3/4] Building site..." -ForegroundColor Yellow
python -m scholarscript build 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed. Check errors above." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit
}
Write-Host ""

# Step 4: Deploy
Write-Host "[4/4] Deploying to GitHub Pages..." -ForegroundColor Yellow

    # Load saved token/repo if available
    $tokenFile = "$projectDir\.github_token"
    $repoFile = "$projectDir\.github_repo"
    if (Test-Path $tokenFile) { $env:GITHUB_TOKEN = (Get-Content $tokenFile -Raw).Trim() }
    if (Test-Path $repoFile) { $env:GITHUB_REPO = (Get-Content $repoFile -Raw).Trim() }

python -m scholarscript deploy 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Deploy failed. Check errors above." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Done! Files published to your website." -ForegroundColor Green
Write-Host "  https://dasguptateach-web.github.io/ScholarScript/" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Green
Write-Host ""

Read-Host "Press Enter to close"
