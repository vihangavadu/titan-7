@echo off
echo Starting TITAN V7.0.3 Docker Build...

docker --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker not found. Please install Docker Desktop.
    pause
    exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker not running. Starting Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    timeout /t 60
    docker info >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Docker still not running. Please start manually.
        pause
        exit /b 1
    )
)

echo Docker is running. Building image...
docker build -t titan-build:latest -f Dockerfile.build .

if errorlevel 1 (
    echo ERROR: Docker image build failed
    pause
    exit /b 1
)

echo Running build container...
docker run -it --rm ^
    -v "%CD%":/workspace ^
    -v titan-build-cache:/var/cache/apt ^
    --cap-add SYS_ADMIN ^
    --device /dev/fuse ^
    --security-opt apparmor:unconfined ^
    titan-build:latest ^
    /usr/local/bin/build-titan.sh

echo.
echo Build complete!
pause
