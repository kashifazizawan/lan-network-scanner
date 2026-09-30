# ============================================================
#  LAN Network Scanner - Windows build script (PowerShell)
#  Produces dist\LanScanner.exe (standalone, no Python needed)
#
#  Run from PowerShell:  .\build_windows.ps1
# ============================================================
$ErrorActionPreference = "Stop"

Write-Host "[1/4] Checking Python..." -ForegroundColor Cyan
python --version
if (-not $?) { throw "Python 3.10+ is required" }

Write-Host "[2/4] Installing dependencies..." -ForegroundColor Cyan
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller pytest

Write-Host "[3/4] Running tests..." -ForegroundColor Cyan
python -m pytest tests -q
if ($LASTEXITCODE -ne 0) { throw "Tests failed - aborting build" }

Write-Host "[4/4] Building executable..." -ForegroundColor Cyan
python -m PyInstaller --clean --noconfirm LanScanner.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed" }

if (Test-Path "dist\LanScanner.exe") {
    Write-Host "`nBuild successful: dist\LanScanner.exe" -ForegroundColor Green
    Write-Host "Copy that single file to any Windows 10/11 64-bit machine."
} else {
    throw "Build FAILED - dist\LanScanner.exe was not created."
}
