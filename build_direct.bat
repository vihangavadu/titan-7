@echo off
set DOCKER_EXE="C:\Program Files\Docker\Docker\resources\bin\docker.exe"
echo Starting TITAN V7.0.3 Docker Build...
echo.

%DOCKER_EXE% --version
if errorlevel 1 (
    echo Docker not accessible, trying to start Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    timeout /t 30
    %DOCKER_EXE% --version
    if errorlevel 1 (
        echo ERROR: Cannot access Docker
        pause
        exit /b 1
    )
)

echo Building Docker image...
%DOCKER_EXE% build -t titan-build:latest -f Dockerfile.build .

if errorlevel 1 (
    echo ERROR: Docker image build failed
    pause
    exit /b 1
)

echo Running build container...
%DOCKER_EXE% run -it --rm ^
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
