$ErrorActionPreference = "Stop"

$IconPath = Join-Path $PSScriptRoot "assets\\bills_duplicate_finder.ico"
$DistPath = Join-Path $PSScriptRoot "dist"
$BuildPath = Join-Path $PSScriptRoot "build"

if (-not (Test-Path $IconPath)) {
    Write-Host ""
    Write-Host "Missing application icon:" -ForegroundColor Yellow
    Write-Host "  $IconPath"
    Write-Host ""
    Write-Host "Place bills_duplicate_finder.ico in the assets folder and run this script again."
    exit 1
}

python -m pip install -r requirements-dev.txt

if (Test-Path $BuildPath) {
    Remove-Item $BuildPath -Recurse -Force
}

python -m PyInstaller --noconfirm --clean --onefile --windowed --name "Bill's Duplicate Finder" --icon $IconPath --add-data "$IconPath;assets" --add-data "duplicate_finder\\ui\\styles.qss;duplicate_finder\\ui" gui.py

Write-Host ""
Write-Host "Build complete:" -ForegroundColor Green
Write-Host "  $DistPath\\Bill's Duplicate Finder.exe"
