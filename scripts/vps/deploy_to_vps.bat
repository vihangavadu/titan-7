@echo off
echo ==========================================
echo Titan-7 VPS Deployment Script
echo Target: 187.77.186.252 (Debian 12)
echo ==========================================
echo.

set VPS_IP=187.77.186.252
set VPS_USER=root
set VPS_PASS=Chilaw@123@llm
set BASE_DIR=C:\Users\Administrator\Downloads\titan-7\titan-7\titan-7

echo [Step 1/4] Uploading setup script...
scp -o StrictHostKeyChecking=no "%BASE_DIR%\scripts\vps\setup_optimized_xrdp_windsurf.sh" %VPS_USER%@%VPS_IP%:/tmp/
if errorlevel 1 (
    echo ERROR: Failed to upload setup script
    echo Please run manually:
    echo scp "%BASE_DIR%\scripts\vps\setup_optimized_xrdp_windsurf.sh" root@187.77.186.252:/tmp/
    pause
    exit /b 1
)
echo   Done!

echo.
echo [Step 2/4] Running setup on VPS...
echo This will take 10-15 minutes. Installing:
echo   - XFCE Desktop + XRDP
echo   - Windsurf IDE
echo   - Google Chrome
echo   - Firefox ESR
echo   - Chromium
echo   - Camoufox
echo   - Multilogin X placeholders
echo.
ssh -o StrictHostKeyChecking=no %VPS_USER%@%VPS_IP% "bash /tmp/setup_optimized_xrdp_windsurf.sh"
if errorlevel 1 (
    echo ERROR: Setup script failed
    echo Please run manually:
    echo ssh root@187.77.186.252 "bash /tmp/setup_optimized_xrdp_windsurf.sh"
    pause
    exit /b 1
)
echo   Done!

echo.
echo [Step 3/4] Uploading Titan-7 codebase...
scp -o StrictHostKeyChecking=no "%BASE_DIR%\..\titan-7-complete.zip" %VPS_USER%@%VPS_IP%:/root/workspace/
if errorlevel 1 (
    echo ERROR: Failed to upload codebase
    echo Please run manually:
    echo scp "%BASE_DIR%\..\titan-7-complete.zip" root@187.77.186.252:/root/workspace/
    pause
    exit /b 1
)
echo   Done!

echo.
echo [Step 4/4] Extracting codebase on VPS...
ssh -o StrictHostKeyChecking=no %VPS_USER%@%VPS_IP% "cd /root/workspace && unzip -q titan-7-complete.zip && echo 'Extraction complete'"
echo   Done!

echo.
echo ==========================================
echo ✓ Deployment Complete!
echo ==========================================
echo.
echo VPS is ready! Connect via XRDP:
echo.
echo   Computer: 187.77.186.252:3389
echo   Username: root
echo   Password: Chilaw@123@llm
echo.
echo Desktop shortcuts available:
echo   - Windsurf IDE
echo   - Google Chrome
echo   - Firefox ESR
echo   - Camoufox Browser
echo   - Multilogin X
echo   - Multilogin Luna
echo.
echo Titan-7 codebase location:
echo   /root/workspace/titan-7
echo.
echo To launch Windsurf IDE:
echo   Double-click Windsurf icon on desktop
echo   Or run: windsurf /root/workspace/titan-7
echo.
echo ==========================================
pause
