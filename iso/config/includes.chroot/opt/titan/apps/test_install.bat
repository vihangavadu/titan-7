@echo off
echo Testing TITAN Development Hub Installation
echo ==========================================

:: Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Please install Python 3.7 or higher.
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Python found. Checking version...
python --version

:: Check if main files exist
echo.
echo Checking files...
if exist "titan_dev_hub.py" (
    echo ✓ titan_dev_hub.py found
) else (
    echo ✗ titan_dev_hub.py missing
)

if exist "requirements.txt" (
    echo ✓ requirements.txt found
) else (
    echo ✗ requirements.txt missing
)

if exist "README_DevHub.md" (
    echo ✓ README_DevHub.md found
) else (
    echo ✗ README_DevHub.md missing
)

:: Check directories
echo.
echo Checking directories...
if exist "..\config" (
    echo ✓ config directory exists
) else (
    echo ✗ config directory missing
)

if exist "..\core" (
    echo ✓ core directory exists
) else (
    echo ✗ core directory missing
)

:: Try to import the hub
echo.
echo Testing hub import...
python -c "import sys; sys.path.insert(0, '.'); import titan_dev_hub; print('✓ Hub imports successfully')" 2>nul
if errorlevel 1 (
    echo ✗ Hub import failed
) else (
    echo ✓ Hub imports successfully
)

echo.
echo Installation test complete.
echo.
echo To run the TITAN Development Hub:
echo   1. Install dependencies: python -m pip install -r requirements.txt --user
echo   2. Run the hub: python titan_dev_hub.py
echo   3. Or use the launcher: launch_dev_hub.bat
echo.
pause
