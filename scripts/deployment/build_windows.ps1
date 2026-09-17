# ==============================================================================
# ORION BAS AI DESKTOP - WINDOWS 10/11 STANDALONE BUILD SCRIPT
# Produces standalone ORION.exe with C++20 acceleration and PySide6 UI
# ==============================================================================

[CmdletBinding()]
param (
    [switch]$SkipCppBuild = $false,
    [switch]$DebugBuild = $false,
    [string]$PythonExe = "python.exe"
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  ORION BAS Desktop System - Windows Deployment Packager    " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$WorkspaceRoot = (Get-Item $PSScriptRoot).Parent.Parent.FullName
Set-Location $WorkspaceRoot

# 1. Environment Verification
Write-Host "[1/6] Verifying toolchains..." -ForegroundColor Yellow

$PythonVersion = & $PythonExe --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Python not found! Ensure Python 3.11+ is installed and on PATH."
}
Write-Host "  Found Python: $PythonVersion" -ForegroundColor Green

if (-not $SkipCppBuild) {
    $CmakeVersion = cmake --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "CMake not found! Please install CMake 3.20+."
    }
    Write-Host "  Found CMake: $($CmakeVersion | Select-Object -First 1)" -ForegroundColor Green
}

# 2. Virtual Environment Setup & Dependencies
Write-Host "[2/6] Checking Python dependencies..." -ForegroundColor Yellow
& $PythonExe -m pip install --upgrade pip
& $PythonExe -m pip install -r requirements.txt
& $PythonExe -m pip install pyinstaller cmake pybind11 pyside6

# 3. Native C++ Engine Compilation
if (-not $SkipCppBuild) {
    Write-Host "[3/6] Compiling C++20 Native Engine (orion_native.pyd)..." -ForegroundColor Yellow
    $BuildDir = Join-Path $WorkspaceRoot "build_win"
    if (Test-Path $BuildDir) { Remove-Item -Recurse -Force $BuildDir }
    New-Item -ItemType Directory -Path $BuildDir | Out-Null

    $ConfigType = if ($DebugBuild) { "Debug" } else { "Release" }
    cmake -B $BuildDir -S $WorkspaceRoot -DCMAKE_BUILD_TYPE=$ConfigType -A x64
    cmake --build $BuildDir --config $ConfigType --parallel

    # Locate and copy built .pyd to workspace root
    $BuiltPyd = Get-ChildItem -Path $BuildDir -Recurse -Filter "orion_native*.pyd" | Select-Object -First 1
    if ($BuiltPyd) {
        Copy-Item -Path $BuiltPyd.FullName -Destination $WorkspaceRoot -Force
        Write-Host "  Copied $($BuiltPyd.Name) to workspace root." -ForegroundColor Green
    } else {
        Write-Warning "Could not find built orion_native.pyd; will proceed with pure Python fallback."
    }
} else {
    Write-Host "[3/6] Skipping C++ build step as requested." -ForegroundColor DarkGray
}

# 4. Standalone Executable Packaging via PyInstaller
Write-Host "[4/6] Packaging native executable with PyInstaller..." -ForegroundColor Yellow
$SpecFile = Join-Path $WorkspaceRoot "build.spec"
if (-not (Test-Path $SpecFile)) {
    Write-Error "build.spec not found at $SpecFile!"
}

& $PythonExe -m PyInstaller "$SpecFile" --noconfirm --clean

# 5. Validation of Distribution Directory
Write-Host "[5/6] Validating output bundle..." -ForegroundColor Yellow
$DistDir = Join-Path $WorkspaceRoot "dist\ORION"
$ExePath = Join-Path $DistDir "ORION.exe"

if (-not (Test-Path $ExePath)) {
    Write-Error "Build verification failed: $ExePath does not exist!"
}
Write-Host "  Verified: $ExePath exists." -ForegroundColor Green

# 6. Archive and Checksum Generation
Write-Host "[6/6] Generating deployment archive and SHA256..." -ForegroundColor Yellow
$ZipPath = Join-Path $WorkspaceRoot "dist\ORION_Windows_x64.zip"
if (Test-Path $ZipPath) { Remove-Item -Force $ZipPath }

Compress-Archive -Path "$DistDir\*" -DestinationPath $ZipPath -CompressionLevel Optimal
$Hash = (Get-FileHash -Path $ZipPath -Algorithm SHA256).Hash

$Manifest = @"
============================================================
ORION BAS AI DESKTOP - WINDOWS RELEASE MANIFEST
============================================================
Package:     ORION_Windows_x64.zip
Timestamp:   $((Get-Date).ToUniversalTime().ToString("yyyy-MM-dd HH:mm:ss UTC"))
SHA256:      $Hash
Target Arch: Windows 10 / 11 x64
Runtime:     Offline Air-Gapped Standalone
AI Models:   YOLOv11 Object, YOLOv11 Pose, Fine-Tuned BAS ST-GCN HAR
============================================================
"@

Write-Host $Manifest -ForegroundColor Cyan
Set-Content -Path (Join-Path $WorkspaceRoot "dist\RELEASE_MANIFEST.txt") -Value $Manifest

Write-Host "`nBuild succeeded! Distributable ready at: $ZipPath" -ForegroundColor Green
