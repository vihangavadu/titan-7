@echo off
title TITAN V7.0.3 Docker Build

echo.
echo TITAN V7.0.3 SINGULARITY - Docker Desktop Build
echo Authority: Dva.12 | Status: OBLIVION_ACTIVE
echo.

if not exist "iso\finalize_titan.sh" (
    echo ERROR: Not in titan-main directory
    echo Run this from: C:\path\to\titan-main\
    pause
    exit /b 1
)

docker --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker Desktop not installed
    echo Install from: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker Desktop not running
    echo Start Docker Desktop and wait for initialization
    pause
    exit /b 1
)

echo Docker Desktop: Running

docker images titan-build --format "{{.Repository}}:{{.Tag}}" | findstr "titan-build:latest" >nul
if errorlevel 1 (
    echo Building Docker image...
    echo This will take 5-10 minutes...
    docker build -t titan-build:latest -f Dockerfile.build .
    if errorlevel 1 (
        echo ERROR: Docker image build failed
        pause
        exit /b 1
    )
) else (
    echo Docker image exists: titan-build:latest
)

echo Cleaning previous containers...
for /f "tokens=*" %%i in ('docker ps -a --filter "name=titan-build-" --format "{{.Names}}" 2^>nul') do (
    docker rm -f %%i >nul 2>&1
)

docker volume create titan-build-cache >nul 2>&1

echo.
echo CONTAINER BUILD STARTING
echo This will take 30-60 minutes
echo.

docker run -it --rm ^
    -v "%CD%":/workspace ^
    -v titan-build-cache:/var/cache/apt ^
    -v titan-build-cache:/var/lib/apt/lists ^
    --cap-add SYS_ADMIN ^
    --device /dev/fuse ^
    --security-opt apparmor:unconfined ^
    titan-build:latest ^
    /usr/local/bin/build-titan.sh

if errorlevel 1 (
    echo.
    echo CONTAINER BUILD FAILED
    pause
    exit /b 1
)

echo.
echo CONTAINER BUILD COMPLETE
echo.

if exist "iso\titan-v7.0.3-singularity.iso" (
    echo ISO created: iso\titan-v7.0.3-singularity.iso
    
    for %%F in ("iso\titan-v7.0.3-singularity.iso") do (
        set size=%%~zF
        set /a sizeMB=!size! / 1048576
    )
    
    echo Size: !sizeMB! MB
    
    if not exist "iso\titan-v7.0.3-singularity.iso.sha256" (
        echo Generating checksum...
        docker run --rm -v "%CD%":/workspace alpine sh -c "cd /workspace/iso && sha256sum titan-v7.0.3-singularity.iso > titan-v7.0.3-singularity.iso.sha256"
    )
    
    echo.
    echo BUILD COMPLETE
    echo ISO: %CD%\iso\titan-v7.0.3-singularity.iso
    echo Size: !sizeMB! MB
    echo SHA256: %CD%\iso\titan-v7.0.3-singularity.iso.sha256
    echo.
    echo Next Steps:
    echo 1. Test ISO in VirtualBox or QEMU
    echo 2. Write to USB (DESTRUCTIVE): 
    echo    In WSL: sudo dd if="/mnt/c/%CD:\=%%" of=/dev/sdX bs=4M
    echo.
) else (
    echo ERROR: ISO file not found
    echo Check build logs above for errors
)

echo.
echo TITAN V7.0.3 Docker build complete!
echo.
pause
