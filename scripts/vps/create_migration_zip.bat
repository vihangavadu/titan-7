@echo off
echo ==========================================
echo Titan-7 Migration Package Creator
echo ==========================================
echo.

set BASE_DIR=C:\Users\Administrator\Downloads\titan-7\titan-7\titan-7
set OUTPUT_DIR=C:\Users\Administrator\Downloads\titan-7\titan-7
set TIMESTAMP=%date:~-4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%

echo [1/2] Creating Titan-7 complete archive...
cd "%BASE_DIR%\.."
powershell -Command "Compress-Archive -Path '%BASE_DIR%' -DestinationPath '%OUTPUT_DIR%\titan-7-complete.zip' -CompressionLevel Optimal -Force"
echo   Done: titan-7-complete.zip

echo.
echo [2/2] Archive ready for upload
echo.
echo ==========================================
echo Next Steps:
echo ==========================================
echo.
echo 1. Upload setup script to VPS:
echo    scp "%BASE_DIR%\scripts\vps\setup_optimized_xrdp_windsurf.sh" root@187.77.186.252:/tmp/
echo.
echo 2. Run setup on VPS:
echo    ssh root@187.77.186.252 "bash /tmp/setup_optimized_xrdp_windsurf.sh"
echo.
echo 3. Upload codebase:
echo    scp "%OUTPUT_DIR%\titan-7-complete.zip" root@187.77.186.252:/root/workspace/
echo.
echo 4. Connect via XRDP:
echo    mstsc /v:187.77.186.252:3389
echo    Username: root
echo    Password: Chilaw@123@llm
echo.
echo ==========================================
pause
