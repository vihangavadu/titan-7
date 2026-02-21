@echo off
set VPS_HOST=72.62.72.48
set VPS_USER=root
set VPS_PASS=Xt7mKp9wRv3n.Jq2026
set SCRIPT_PATH=%~dp0vps_verify_real.sh

echo Connecting to VPS...
echo.

REM Try using Git SSH with password
"C:\Program Files\Git\usr\bin\ssh.exe" -o StrictHostKeyChecking=no -o PasswordAuthentication=yes %VPS_USER%@%VPS_HOST% "cd /opt/titan && echo 'Connected successfully' && whoami && pwd"

if %ERRORLEVEL% NEQ 0 (
    echo SSH connection failed
    pause
    exit /b 1
)

echo.
echo Running verification script...
echo.

"C:\Program Files\Git\usr\bin\ssh.exe" -o StrictHostKeyChecking=no -o PasswordAuthentication=yes %VPS_USER%@%VPS_HOST% < "%SCRIPT_PATH%"

pause
