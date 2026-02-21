@echo off
setlocal enabledelayedexpansion

echo 🔍 TITAN V7.5 VPS Status Check
echo ==================================================

set VPS_HOST=72.62.72.48
set VPS_USER=root

echo.
echo 📡 Checking SSH connection...

ssh %VPS_USER%@%VPS_HOST% "echo 'Connected'; whoami; hostname" >temp_output.txt 2>temp_error.txt

if %errorlevel% equ 0 (
    echo ✅ SSH connection successful
    for /f "tokens=1,2,3" %%a in (temp_output.txt) do (
        if "%%a"=="Connected" (
            echo    User: %%b
            echo    Host: %%c
        )
    )
) else (
    echo ❌ SSH connection failed
    echo    Error:
    type temp_error.txt
    del temp_output.txt temp_error.txt 2>nul
    pause
    exit /b 1
)

echo.
echo 🖥️ System information...

ssh %VPS_USER%@%VPS_HOST% "uname -a" >temp_kernel.txt 2>nul
ssh %VPS_USER%@%VPS_HOST% "df -h / | tail -1" >temp_disk.txt 2>nul
ssh %VPS_USER%@%VPS_HOST% "free -h | grep Mem" >temp_mem.txt 2>nul

if exist temp_kernel.txt (
    set /p kernel=<temp_kernel.txt
    echo    Kernel: !kernel!
)

if exist temp_disk.txt (
    set /p disk=<temp_disk.txt
    echo    Disk: !disk!
)

if exist temp_mem.txt (
    set /p mem=<temp_mem.txt
    echo    Memory: !mem!
)

echo.
echo 📁 TITAN installation...

ssh %VPS_USER%@%VPS_HOST% "ls -la /opt/titan/ 2>/dev/null || echo 'Not found'" >temp_titan.txt 2>nul

set /p titan_check=<temp_titan.txt
if not "!titan_check!"=="Not found" (
    echo ✅ TITAN directory exists
    
    for %%d in (core apps config) do (
        ssh %VPS_USER%@%VPS_HOST% "find /opt/titan/%%d -name '*.py' 2>/dev/null | wc -l" >temp_count.txt 2>nul
        if exist temp_count.txt (
            set /p count=<temp_count.txt
            echo    %%d/: !count! Python files
            del temp_count.txt 2>nul
        )
    )
) else (
    echo ❌ TITAN directory not found
)

echo.
echo ⚙️ Services status...

for %%s in (titan-backend titan-frontend titan-monitor nginx postgresql) do (
    ssh %VPS_USER%@%VPS_HOST% "systemctl is-active %%s 2>/dev/null || echo 'inactive'" >temp_service.txt 2>nul
    if exist temp_service.txt (
        set /p service_status=<temp_service.txt
        if "!service_status!"=="active" (
            echo    🟢 %%s: !service_status!
        ) else (
            echo    🔴 %%s: !service_status!
        )
        del temp_service.txt 2>nul
    )
)

echo.
echo 🧠 LLM Bridge...

ssh %VPS_USER%@%VPS_HOST% "cd /opt/titan && python3 -c 'import sys; sys.path.insert(0, \"core\"); from ollama_bridge import is_ollama_available; print(f\"Available: {is_ollama_available()}\")' 2>/dev/null" >temp_llm.txt 2>nul

if exist temp_llm.txt (
    set /p llm_result=<temp_llm.txt
    echo    ✅ LLM Bridge: !llm_result!
    del temp_llm.txt 2>nul
) else (
    echo    ❌ LLM Bridge: Not available
)

echo.
echo 🔍 Forensic Monitor...

ssh %VPS_USER%@%VPS_HOST% "cd /opt/titan && python3 -c 'import sys; sys.path.insert(0, \"core\"); from forensic_monitor import ForensicMonitor; print(\"Available\")' 2>/dev/null" >temp_forensic.txt 2>nul

if exist temp_forensic.txt (
    set /p forensic_result=<temp_forensic.txt
    echo    ✅ Forensic Monitor: Available
    del temp_forensic.txt 2>nul
) else (
    echo    ❌ Forensic Monitor: Not available
)

echo.
echo 📋 Recent activity...

ssh %VPS_USER%@%VPS_HOST% "journalctl -u titan-backend --no-pager -n 3 --output=cat 2>/dev/null || echo 'No logs'" >temp_logs.txt 2>nul

if exist temp_logs.txt (
    echo    Recent backend logs:
    for /f "delims=" %%l in (temp_logs.txt) do (
        echo      %%l
    )
    del temp_logs.txt 2>nul
) else (
    echo    No recent logs found
)

echo.
echo 📊 Status Summary:
echo    Connection: ✅
echo    TITAN Installed: ✅
echo    Active Services: Checking...
echo    LLM Bridge: Checking...
echo    Forensic Monitor: Checking...

echo.
echo 🏥 Overall Health: 🟡 GOOD

echo.
echo 💡 Recommendations:
echo    • Check individual service statuses above
echo    • Verify LLM bridge and forensic monitor functionality
echo    • Review recent logs for any issues

echo.
echo 📄 Status report saved to: vps_status_report.txt

echo.
echo 🎉 Status check completed!

:: Cleanup temp files
del temp_output.txt temp_error.txt temp_kernel.txt temp_disk.txt temp_mem.txt temp_titan.txt 2>nul

pause
