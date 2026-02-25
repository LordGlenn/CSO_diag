@echo off
REM Build script for Windows
REM Creates a standalone executable with bundled Chromium browser

echo === Zyxel CSO Diagnostics Collector - Build Script ===

REM Step 1: Install dependencies
echo [1/4] Installing Python dependencies...
pip install playwright pyinstaller

REM Step 2: Install Chromium browser
echo [2/4] Installing Chromium browser for Playwright...
python -m playwright install chromium

REM Step 3: Find Playwright Chromium path
echo [3/4] Locating Chromium browser...
set "PW_CACHE=%LOCALAPPDATA%\ms-playwright"

for /f "delims=" %%d in ('dir /b /ad /o-n "%PW_CACHE%\chromium-*" 2^>nul') do (
    set "CHROMIUM_DIR=%PW_CACHE%\%%d"
    goto :found
)
echo ERROR: Could not find Playwright Chromium installation.
echo Please run: python -m playwright install chromium
exit /b 1

:found
echo   Found Chromium at: %CHROMIUM_DIR%

REM Step 4: Build with PyInstaller
echo [4/4] Building executable with PyInstaller...
pyinstaller ^
    --onedir ^
    --name cso_diag ^
    --add-data "%CHROMIUM_DIR%;playwright\chromium" ^
    --hidden-import playwright ^
    --hidden-import playwright.sync_api ^
    --hidden-import playwright._impl ^
    --hidden-import playwright._impl._driver ^
    --noconfirm ^
    --clean ^
    cso_diag.py

echo.
echo === Build complete! ===
echo Output directory: dist\cso_diag\
echo.
echo Usage:
echo   dist\cso_diag\cso_diag.exe ^<device_ip^> ^<username^> ^<password^>
echo.
echo To distribute, zip the entire dist\cso_diag\ directory.
