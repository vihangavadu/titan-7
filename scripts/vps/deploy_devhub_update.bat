@echo off
:: ═══════════════════════════════════════════════════════════════════
:: Deploy updated titan_dev_hub.py + install_opencode_omo.sh to VPS
:: Uses plink/pscp (PuTTY) or Windows OpenSSH with password prompt
:: ═══════════════════════════════════════════════════════════════════
setlocal

set VPS_IP=187.77.186.252
set VPS_USER=root
set BASE_DIR=C:\Users\Administrator\Downloads\titan-7\titan-7\titan-7
set DEV_HUB_SRC=%BASE_DIR%\iso\config\includes.chroot\opt\titan\apps\titan_dev_hub.py
set INSTALL_SRC=%BASE_DIR%\scripts\vps\install_opencode_omo.sh
set SKILL_SRC=%BASE_DIR%\scripts\vps\titan_omo_skill\SKILL.md

echo ═══════════════════════════════════════════════════════
echo  Titan Dev Hub + OpenCode/OmO Deploy to VPS
echo  Target: %VPS_USER%@%VPS_IP%
echo ═══════════════════════════════════════════════════════
echo.

:: ─── Check for pscp (PuTTY) first ───────────────────────────────
where pscp >nul 2>&1
if %errorlevel%==0 (
    echo [MODE] Using PuTTY pscp/plink
    set USE_PUTTY=1
) else (
    echo [MODE] Using Windows OpenSSH (scp/ssh)
    set USE_PUTTY=0
)

echo.
echo [1/4] Uploading titan_dev_hub.py ...
if "%USE_PUTTY%"=="1" (
    pscp -pw "Chilaw@123@llm" -o StrictHostKeyChecking=no "%DEV_HUB_SRC%" %VPS_USER%@%VPS_IP%:/opt/titan/apps/titan_dev_hub.py
) else (
    scp -o StrictHostKeyChecking=no "%DEV_HUB_SRC%" %VPS_USER%@%VPS_IP%:/opt/titan/apps/titan_dev_hub.py
)
if errorlevel 1 (
    echo ERROR: Upload of titan_dev_hub.py failed
    echo.
    echo If SSH is blocked, run this MANUALLY inside the VPS XRDP terminal:
    echo   See: MANUAL_DEPLOY_INSTRUCTIONS.txt
    goto :manual
)
echo   Done.

echo.
echo [2/4] Uploading install_opencode_omo.sh ...
if "%USE_PUTTY%"=="1" (
    pscp -pw "Chilaw@123@llm" -o StrictHostKeyChecking=no "%INSTALL_SRC%" %VPS_USER%@%VPS_IP%:/tmp/install_opencode_omo.sh
) else (
    scp -o StrictHostKeyChecking=no "%INSTALL_SRC%" %VPS_USER%@%VPS_IP%:/tmp/install_opencode_omo.sh
)
if errorlevel 1 (
    echo ERROR: Upload of install_opencode_omo.sh failed
    goto :manual
)
echo   Done.

echo.
echo [3/4] Restarting titan-dev-hub service ...
if "%USE_PUTTY%"=="1" (
    plink -pw "Chilaw@123@llm" -batch %VPS_USER%@%VPS_IP% "systemctl restart titan-dev-hub 2>/dev/null || (pkill -f titan_dev_hub || true) && sleep 1 && nohup python3 /opt/titan/apps/titan_dev_hub.py &>/tmp/titan_dev_hub.log &"
) else (
    ssh -o StrictHostKeyChecking=no %VPS_USER%@%VPS_IP% "systemctl restart titan-dev-hub 2>/dev/null || (pkill -f titan_dev_hub || true) && sleep 1 && nohup python3 /opt/titan/apps/titan_dev_hub.py &>/tmp/titan_dev_hub.log &"
)
if errorlevel 1 (
    echo WARNING: Service restart command failed - may need manual restart
)
echo   Done.

echo.
echo [4/4] Verifying Dev Hub health ...
timeout /t 3 /nobreak >nul
if "%USE_PUTTY%"=="1" (
    plink -pw "Chilaw@123@llm" -batch %VPS_USER%@%VPS_IP% "curl -s http://localhost:8877/api/health"
) else (
    ssh -o StrictHostKeyChecking=no %VPS_USER%@%VPS_IP% "curl -s http://localhost:8877/api/health"
)

echo.
echo ═══════════════════════════════════════════════════════
echo  Deploy complete!
echo  Dev Hub: http://%VPS_IP%:8877
echo  New Agents tab available in the UI
echo.
echo  To install OpenCode on the VPS, run inside XRDP terminal:
echo    bash /tmp/install_opencode_omo.sh
echo ═══════════════════════════════════════════════════════
pause
goto :eof

:manual
echo.
echo ═══════════════════════════════════════════════════════
echo  MANUAL DEPLOYMENT REQUIRED
echo  SSH from this machine is blocked (port 22 timeout).
echo.
echo  Connect via XRDP: 187.77.186.252:3389 (root / Chilaw@123@llm)
echo  Then open a terminal and run the commands in:
echo    %BASE_DIR%\scripts\vps\MANUAL_DEPLOY_INSTRUCTIONS.txt
echo ═══════════════════════════════════════════════════════
pause
