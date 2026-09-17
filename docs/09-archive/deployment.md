# ORION Production Deployment Guide

## 1. Air-Gapped Space Station Deployment

ORION is engineered to operate strictly in **isolated, air-gapped environments** with zero external network connectivity. All models, protocols, speech synthesis engines, and libraries are self-contained within the distributable.

---

## 2. Windows 10/11 Standalone Build (`ORION.exe`)

### 2.1 Prerequisites
- Windows 10 or 11 (64-bit).
- Python 3.11+ installed.
- Microsoft Visual C++ 2022 Build Tools (MSVC v143).
- CMake 3.20+.

### 2.2 Automated Packaging
Run the PowerShell packaging script from an administrative PowerShell prompt:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\deployment\build_windows.ps1
```

### 2.3 Deployment Output
- Executable Folder: `dist\ORION\ORION.exe`
- Standalone Zip Archive: `dist\ORION_Windows_x64.zip`
- Manifest with SHA256: `dist\RELEASE_MANIFEST.txt`

Transfer the `.zip` to the target workstation via approved USB flash storage or internal station optical disc, extract, and execute `ORION.exe`.

---

## 3. macOS Standalone Build

### 3.1 Prerequisites
- macOS 13+ (Ventura or Sonoma on Apple Silicon or Intel).
- Xcode Command Line Tools (`xcode-select --install`).
- CMake 3.20+.

### 3.2 Build Script
```bash
./scripts/deployment/build_macos.sh
```
The packaged application will be generated in `dist/ORION`.

---

## 4. Hardware Connection & Glovebox Setup

1. **Optical Video Sensor (Camera)**:
   - Connect the USB 3.0 / USB-C Glovebox camera.
   - Edit `config/camera.yaml` to specify the camera device index (default: `"0"`) or RTSP/V4L2 path.
   - Recommended resolution: `1280x720` @ 30 FPS.
2. **Audio Annunciators**:
   - Ensure system speakers or astronaut headset is connected for voice guidance and cautionary chimes.
3. **Storage Allocation**:
   - Minimum 10 GB free space for session MP4 recordings and post-mission verification dossiers.
