@echo off
REM Titan-7 Public File Server Launcher
REM Quick launcher for Windows

cd /d "%~dp0.."
cls

echo ========================================================================
echo                    TITAN-7 PUBLIC FILE SERVER
echo ========================================================================
echo.
echo This will start a web server to share the entire Titan-7 folder
echo.

set /p PORT="Enter port number (default 8000): "
if "%PORT%"=="" set PORT=8000

echo.
echo Starting server on port %PORT%...
echo.
echo IMPORTANT: Make sure Windows Firewall allows port %PORT%
echo.

python scripts\titan_file_server.py --port %PORT% --dir "%CD%"

pause
