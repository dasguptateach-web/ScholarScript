$ErrorActionPreference = "Stop"
$appDir = Split-Path -Parent $PSCommandPath
$projectDir = Split-Path -Parent $appDir
$desktop = [Environment]::GetFolderPath("Desktop")
$distDir = "$appDir\dist"
$buildDir = "$appDir\build"

$env:PYTHONHOME = "C:\Users\81\AppData\Local\Programs\Python\Python311"

Write-Host "=== ScholarScript Portable Builder ===" -ForegroundColor Cyan
Write-Host "App dir: $appDir"
Write-Host ""

# Generate a simple icon (green S icon as ICO)
Write-Host "Generating icon..." -ForegroundColor Yellow
$icoDir = "$appDir\assets"
New-Item -ItemType Directory -Path $icoDir -Force | Out-Null

$pyCode = @'
import struct, zlib, os
from pathlib import Path

ico_dir = r"__ICO_DIR__"
ico_path = os.path.join(ico_dir, "icon.ico")

# Create a simple 32x32 RGBA icon - a green "S" on dark background
size = 32
pixels = bytearray()
for y in range(size):
    for x in range(size):
        # Checkerboard background
        cx, cy = x - 16, y - 16
        dist = (cx*cx + cy*cy) ** 0.5
        in_circle = dist < 14
        # S letter shape (simplified)
        in_s = (8 <= x <= 24 and 6 <= y <= 12) or (8 <= x <= 24 and 14 <= y <= 18) or (8 <= x <= 24 and 20 <= y <= 26)
        in_s = in_s and in_circle
        if in_s:
            r, g, b, a = 76, 175, 80, 255  # green
        elif in_circle:
            r, g, b, a = 30, 30, 30, 255  # dark
        else:
            r, g, b, a = 0, 0, 0, 0  # transparent
        pixels.extend([b, g, r, a])

# BMP format as ICO entry
bmp_header = struct.pack('<IHHIIII', 40, size, size*2, 1, 32, 0, len(pixels), 0, 0, 0, 0)
bmp_data = bmp_header + bytes(pixels)

# ICO file
ico_header = struct.pack('<HHH', 0, 1, 1)
entry = struct.pack('<BBBBHHII', size, size, 0, 0, 1, 32, len(bmp_data), 22)
with open(ico_path, 'wb') as f:
    f.write(ico_header + entry + bmp_data)
print(f"Icon created: {ico_path}")
'@.Replace("__ICO_DIR__", $icoDir.Replace("\", "\\"))

& "$env:PYTHONHOME\python.exe" -c $pyCode

# Create the version info file
Write-Host "Creating version info..." -ForegroundColor Yellow
@"
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1,0,0,0),
    prodvers=(1,0,0,0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0,0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'040904B0',
          [StringStruct(u'CompanyName', u'ScholarScript'),
           StringStruct(u'FileDescription', u'S ScholarScript Portable - Upload & Publish'),
           StringStruct(u'FileVersion', u'1.0.0.0'),
           StringStruct(u'InternalName', u'S ScholarScript Portable'),
           StringStruct(u'LegalCopyright', u''),
           StringStruct(u'OriginalFilename', u'ScholarScriptPortable.exe'),
           StringStruct(u'ProductName', u'S ScholarScript Portable'),
           StringStruct(u'ProductVersion', u'1.0.0.0')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"@ | Out-File -FilePath "$appDir\version_info.txt" -Encoding utf8

# Build with PyInstaller
Write-Host "Building executable with PyInstaller..." -ForegroundColor Yellow
$hiddenImports = @(
    "docx", "pdfplumber", "jinja2", "PIL", "pdf2image", "pytesseract",
    "odf", "striprtf", "tex", "lxml"
)

$pyiArgs = @(
    "--onefile",
    "--windowed",
    "--name", "ScholarScriptPortable",
    "--icon", "$icoDir\icon.ico",
    "--version-file", "$appDir\version_info.txt",
    "--distpath", "$distDir",
    "--workpath", "$buildDir",
    "--add-data", "$icoDir\icon.ico;assets",
    "--add-data", "$appDir\scholarscript;scholarscript",
    "--hidden-import", "docx",
    "--hidden-import", "pdfplumber",
    "--hidden-import", "jinja2",
    "--hidden-import", "PIL",
    "--hidden-import", "docx.oxml.ns",
    "--hidden-import", "lxml",
    "--collect-all", "scholarscript",
    "--clean",
    "-y",
    "$appDir\main.py"
)

& "$env:PYTHONHOME\Scripts\pyinstaller.exe" $pyiArgs 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller FAILED" -ForegroundColor Red
    exit 1
}

$exePath = "$distDir\ScholarScriptPortable.exe"
if (Test-Path $exePath) {
    $finalPath = "$desktop\ScholarScriptPortable.exe"
    Copy-Item -LiteralPath $exePath -Destination $finalPath -Force
    Write-Host ""
    Write-Host "=== BUILD SUCCESSFUL ===" -ForegroundColor Green
    Write-Host "Executable: $finalPath" -ForegroundColor Green
    Write-Host "Size: $((Get-Item $finalPath).Length / 1MB -as [int]) MB" -ForegroundColor Green
    Write-Host ""
    Write-Host "To use on any Windows laptop:" -ForegroundColor Cyan
    Write-Host "  1. Copy ScholarScriptPortable.exe to the laptop"
    Write-Host "  2. Run it (no install needed)"
    Write-Host "  3. Configure GitHub Token in Settings"
    Write-Host "  4. Drop files in the drop folder"
    Write-Host "  5. App auto-processes and deploys"
} else {
    Write-Host "Build failed - output not found" -ForegroundColor Red
}

# Cleanup build artifacts
Remove-Item -LiteralPath $buildDir -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$appDir\*.spec" -ErrorAction SilentlyContinue
Write-Host "Cleanup done."
