@echo off
:: TITAN Development Hub Launcher for Windows
setlocal enabledelayedexpansion

echo ===============================================
echo        TITAN OS Development Hub
echo ===============================================
echo.

:: Set TITAN root path
set "TITAN_ROOT=%~dp0..\.."
set "DEV_HUB=%TITAN_ROOT%\apps\titan_dev_hub.py"
set "CONFIG_DIR=%TITAN_ROOT%\config"
set "SESSIONS_DIR=%TITAN_ROOT%\sessions"

:: Create necessary directories
if not exist "%SESSIONS_DIR%" mkdir "%SESSIONS_DIR%"
if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"

:: Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is required but not installed
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python version: %PYTHON_VERSION%

:: Check if Dev Hub exists
if not exist "%DEV_HUB%" (
    echo Error: TITAN Dev Hub not found at %DEV_HUB%
    pause
    exit /b 1
)

:: Install dependencies
echo Checking dependencies...
if exist "%TITAN_ROOT%\apps\requirements.txt" (
    python -m pip install -r "%TITAN_ROOT%\apps\requirements.txt" --user --quiet
    echo Dependencies checked
)

:: Set environment variables
set "PYTHONPATH=%TITAN_ROOT%\core;%PYTHONPATH%"
set "TITAN_ROOT=%TITAN_ROOT%"
set "TITAN_DEV_MODE=true"

:: Check for Git
if exist "%TITAN_ROOT%\.git" (
    echo Git repository detected
    cd /d "%TITAN_ROOT%"
    
    :: Get current branch
    for /f "tokens=*" %%i in ('git branch --show-current 2^>nul') do set BRANCH=%%i
    if not defined BRANCH set BRANCH=unknown
    echo Current branch: !BRANCH!
) else (
    echo Not a Git repository - version control limited
)

:: Parse command line arguments
set MODE=gui
set DEBUG=false

:parse_args
if "%~1"=="" goto :start
if /i "%~1"=="--cli" (
    set MODE=cli
    shift
    goto :parse_args
)
if /i "%~1"=="--gui" (
    set MODE=gui
    shift
    goto :parse_args
)
if /i "%~1"=="--debug" (
    set DEBUG=true
    shift
    goto :parse_args
)
if /i "%~1"=="--help" goto :show_help
echo Unknown option: %~1
pause
exit /b 1

:show_help
echo TITAN Development Hub Launcher
echo.
echo Usage: %~nx0 [OPTIONS]
echo.
echo Options:
echo   --cli      Force CLI mode
echo   --gui      Force GUI mode (default)
echo   --debug    Enable debug logging
echo   --help     Show this help
echo.
pause
exit /b 0

:start
echo.
echo Launching TITAN Development Hub...
echo Mode: %MODE%

if "%DEBUG%"=="true" (
    set "TITAN_DEBUG=true"
    echo Debug mode enabled
)

if "%MODE%"=="gui" (
    echo Starting GUI interface...
    python "%DEV_HUB%" --gui
) else (
    echo Starting CLI interface...
    python "%DEV_HUB%" --cli
)

:: Check exit status
if %errorlevel% equ 0 (
    echo.
    echo Session completed successfully
    
    :: Show latest session
    for /f "delims=" %%i in ('dir /b /o-d "%SESSIONS_DIR%\session_*.json" 2^>nul') do (
        echo Session saved: %%i
        goto :done
    )
) else (
    echo Session ended with errors
    pause
    exit /b 1
)

:done
echo ===============================================
pause
