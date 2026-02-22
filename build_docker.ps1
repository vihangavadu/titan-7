# ═══════════════════════════════════════════════════════════════════════════
# TITAN V8.1 — DOCKER DESKTOP POWERSHELL SCRIPT
# AUTHORITY: Dva.12 | STATUS: OBLIVION_ACTIVE
# PURPOSE: Build Titan ISO using Docker Desktop on Windows
#
# Prerequisites:
#   - Docker Desktop for Windows installed and running
#   - WSL2 enabled in Docker Desktop
#   - This script in titan-main directory
#
# Usage:
#   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
#   .\build_docker.ps1
# ═══════════════════════════════════════════════════════════════════════════

param(
    [switch]$SkipBuild,
    [switch]$Clean,
    [switch]$Help
)

# Colors for PowerShell
$Colors = @{
    Red = "Red"
    Green = "Green"
    Yellow = "Yellow"
    Blue = "Blue"
    Cyan = "Cyan"
    White = "White"
}

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Colors[$Color]
}

function Show-Help {
    Write-ColorOutput "TITAN V8.1 Docker Build Script" "Cyan"
    Write-ColorOutput ""
    Write-ColorOutput "Usage:" "White"
    Write-ColorOutput "  .\build_docker.ps1 [options]" "White"
    Write-ColorOutput ""
    Write-ColorOutput "Options:" "White"
    Write-ColorOutput "  -SkipBuild    Skip Docker image build (use existing)" "Yellow"
    Write-ColorOutput "  -Clean        Clean Docker images and containers" "Yellow"
    Write-ColorOutput "  -Help         Show this help message" "Yellow"
    Write-ColorOutput ""
    Write-ColorOutput "Examples:" "White"
    Write-ColorOutput "  .\build_docker.ps1                    # Full build" "Green"
    Write-ColorOutput "  .\build_docker.ps1 -SkipBuild         # Use existing image" "Green"
    Write-ColorOutput "  .\build_docker.ps1 -Clean             # Clean up" "Yellow"
    exit 0
}

if ($Help) {
    Show-Help
}

# Show header
Write-ColorOutput "╔══════════════════════════════════════════════════════════════╗" "Cyan"
Write-ColorOutput "║  TITAN V8.1 SINGULARITY — Docker Desktop Build           ║" "Cyan"
Write-ColorOutput "║  Authority: Dva.12 | Status: OBLIVION_ACTIVE               ║" "Cyan"
Write-ColorOutput "╚══════════════════════════════════════════════════════════════╝" "Cyan"
Write-ColorOutput ""

# Check if we're in the right directory
if (-not (Test-Path "iso\finalize_titan.sh")) {
    Write-ColorOutput "[!] ERROR: Not in titan-main directory" "Red"
    Write-ColorOutput "    Run this script from: C:\path\to\titan-main\" "Yellow"
    exit 1
}

# Clean option
if ($Clean) {
    Write-ColorOutput "[*] Cleaning Docker environment..." "Yellow"
    
    # Stop and remove containers
    docker ps -a --filter "name=titan-build-" --format "{{.Names}}" | ForEach-Object {
        Write-ColorOutput "  Removing container: $_" "Yellow"
        docker rm -f $_ 2>$null
    }
    
    # Remove images
    docker images titan-build --format "{{.Repository}}:{{.Tag}}" | ForEach-Object {
        Write-ColorOutput "  Removing image: $_" "Yellow"
        docker rmi $_ 2>$null
    }
    
    # Remove volumes
    docker volume ls --filter "name=titan-build" --format "{{.Name}}" | ForEach-Object {
        Write-ColorOutput "  Removing volume: $_" "Yellow"
        docker volume rm $_ 2>$null
    }
    
    Write-ColorOutput "[+] Docker cleanup complete" "Green"
    exit 0
}

# Phase 1: Check Docker Desktop
Write-ColorOutput "[1/5] Checking Docker Desktop..." "Blue"

try {
    $DockerVersion = docker --version 2>$null
    if ($LASTEXITCODE -ne 0) { throw "Docker not found" }
    Write-ColorOutput "  [+] Docker: $DockerVersion" "Green"
}
catch {
    Write-ColorOutput "[!] ERROR: Docker Desktop not installed or not running" "Red"
    Write-ColorOutput "    Install Docker Desktop for Windows:" "Yellow"
    Write-ColorOutput "    https://www.docker.com/products/docker-desktop" "Yellow"
    exit 1
}

try {
    docker info | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Docker not running" }
    Write-ColorOutput "  [+] Docker daemon: Running" "Green"
}
catch {
    Write-ColorOutput "[!] ERROR: Docker Desktop not running" "Red"
    Write-ColorOutput "    Start Docker Desktop and wait for it to fully initialize" "Yellow"
    exit 1
}

# Check WSL2 integration
try {
    $WSLStatus = docker run --rm alpine uname -r 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "  [+] WSL2 integration: Working" "Green"
    }
}
catch {
    Write-ColorOutput "[!] WARNING: WSL2 integration may have issues" "Yellow"
}

# Check disk space
$Drive = Get-Location | Select-Object -ExpandProperty Drive
$Disk = Get-PSDrive -Name $Drive.Name.Substring(0,1)
$FreeGB = [math]::Round($Disk.Free / 1GB, 1)
if ($FreeGB -lt 10) {
    Write-ColorOutput "[!] ERROR: Insufficient disk space ($($FreeGB)GB < 10GB required)" "Red"
    exit 1
}
Write-ColorOutput "  [+] Available disk: ${FreeGB}GB" "Green"

# Phase 2: Build Docker Image
Write-ColorOutput "[2/5] Building Docker Image..." "Blue"

$ImageName = "titan-build:latest"
$ImageExists = docker images --filter "reference=$ImageName" --format "{{.Repository}}:{{.Tag}}"

if ($ImageExists) {
    Write-ColorOutput "  [!] Docker image '$ImageName' already exists" "Yellow"
    if (-not $SkipBuild) {
        $Rebuild = Read-Host "  Rebuild? (y/N)"
        if ($Rebuild -eq 'y' -or $Rebuild -eq 'Y') {
            Write-ColorOutput "  [*] Rebuilding image..." "Yellow"
            docker build -t $ImageName -f Dockerfile.build .
            if ($LASTEXITCODE -ne 0) {
                Write-ColorOutput "[!] ERROR: Docker image build failed" "Red"
                exit 1
            }
        } else {
            Write-ColorOutput "  [+] Using existing image" "Green"
        }
    } else {
        Write-ColorOutput "  [+] Using existing image (skip build)" "Green"
    }
} else {
    Write-ColorOutput "  [*] Building Docker image..." "Yellow"
    Write-ColorOutput "    This will download Debian 12 and install dependencies (5-10 minutes)" "Cyan"
    
    docker build -t $ImageName -f Dockerfile.build .
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput "[!] ERROR: Docker image build failed" "Red"
        exit 1
    }
}

Write-ColorOutput "  [+] Docker image ready: $ImageName" "Green"

# Phase 3: Prepare Build
Write-ColorOutput "[3/5] Preparing Build Environment..." "Blue"

# Clean previous containers
$OldContainers = docker ps -a --filter "name=titan-build-" --format "{{.Names}}"
if ($OldContainers) {
    Write-ColorOutput "  [*] Cleaning previous containers..." "Yellow"
    $OldContainers | ForEach-Object {
        docker rm -f $_ 2>$null
    }
}

# Create volume for cache
docker volume create titan-build-cache 2>$null
Write-ColorOutput "  [+] Environment prepared" "Green"

# Phase 4: Build ISO
Write-ColorOutput "[4/5] Building ISO in Container..." "Blue"
Write-ColorOutput ""
Write-ColorOutput "╔══════════════════════════════════════════════════════════════╗" "Cyan"
Write-ColorOutput "║  CONTAINER BUILD STARTING                                 ║" "Cyan"
Write-ColorOutput "║  This will take 30-60 minutes                              ║" "Cyan"
Write-ColorOutput "║  You can monitor progress below                           ║" "Cyan"
Write-ColorOutput "╚══════════════════════════════════════════════════════════════╝" "Cyan"
Write-ColorOutput ""

# Get current directory for volume mount
$CurrentDir = Get-Location | Select-Object -ExpandProperty Path
$ContainerName = "titan-build-$(Get-Date -Format 'yyyyMMddHHmmss')"

# Run build container
docker run -it --rm `
    --name $ContainerName `
    -v "${CurrentDir}:/workspace" `
    -v titan-build-cache:/var/cache/apt `
    -v titan-build-cache:/var/lib/apt/lists `
    --cap-add SYS_ADMIN `
    --device /dev/fuse `
    --security-opt apparmor:unconfined `
    $ImageName `
    /usr/local/bin/build-titan.sh

$BuildExit = $LASTEXITCODE

Write-ColorOutput ""
if ($BuildExit -eq 0) {
    Write-ColorOutput "╔══════════════════════════════════════════════════════════════╗" "Green"
    Write-ColorOutput "║  CONTAINER BUILD COMPLETE                                ║" "Green"
    Write-ColorOutput "╚══════════════════════════════════════════════════════════════╝" "Green"
} else {
    Write-ColorOutput "╔══════════════════════════════════════════════════════════════╗" "Red"
    Write-ColorOutput "║  CONTAINER BUILD FAILED                                   ║" "Red"
    Write-ColorOutput "║  Exit code: $BuildExit                                           ║" "Red"
    Write-ColorOutput "╚══════════════════════════════════════════════════════════════╝" "Red"
    exit $BuildExit
}

# Phase 5: Verify Output
Write-ColorOutput "[5/5] Verifying Output..." "Blue"

$ISOFile = Join-Path $CurrentDir "iso\titan-v7.0.3-singularity.iso"

if (Test-Path $ISOFile) {
    $ISOSize = (Get-Item $ISOFile).Length / 1GB
    $ISOSizeMB = [math]::Round($ISOSize * 1024, 2)
    Write-ColorOutput "  [+] ISO created: $ISOFile" "Green"
    Write-ColorOutput "  [+] Size: ${ISOSizeMB}MB" "Green"
    
    # Generate checksum if missing
    $SHAFile = "$ISOFile.sha256"
    if (-not (Test-Path $SHAFile)) {
        Write-ColorOutput "  [*] Generating checksum..." "Yellow"
        $Hash = Get-FileHash $ISOFile -Algorithm SHA256
        "$($Hash.Hash)  titan-v7.0.3-singularity.iso" | Out-File -FilePath $SHAFile -Encoding UTF8
    }
    
    # Verify checksum
    if (Test-Path $SHAFile) {
        Write-ColorOutput "  [*] Verifying checksum..." "Yellow"
        $Hash = Get-FileHash $ISOFile -Algorithm SHA256
        $ExpectedHash = (Get-Content $SHAFile).Split(' ')[0]
        if ($Hash.Hash -eq $ExpectedHash) {
            Write-ColorOutput "  [+] Checksum verified" "Green"
        } else {
            Write-ColorOutput "  [!] Checksum mismatch!" "Red"
        }
    }
    
    Write-ColorOutput ""
    Write-ColorOutput "╔══════════════════════════════════════════════════════════════╗" "Green"
    Write-ColorOutput "║  BUILD COMPLETE                                             ║" "Green"
    Write-ColorOutput "╠══════════════════════════════════════════════════════════════╣" "Green"
    Write-ColorOutput "║  ISO:        $ISOFile" "White"
    Write-ColorOutput "║  Size:       ${ISOSizeMB}MB" "White"
    Write-ColorOutput "║  SHA256:     $SHAFile" "White"
    Write-ColorOutput "╚══════════════════════════════════════════════════════════════╝" "Green"
    Write-ColorOutput ""
    Write-ColorOutput "Next Steps:" "Cyan"
    Write-ColorOutput ""
    Write-ColorOutput "1. Test ISO in VM:" "White"
    Write-ColorOutput "   qemu-system-x86_64 -m 4096 -enable-kvm -cdrom `"$ISOFile`"" "Yellow"
    Write-ColorOutput ""
    Write-ColorOutput "2. Write to USB (DESTRUCTIVE):" "White"
    Write-ColorOutput "   In WSL: sudo dd if=`"/mnt/c/titan-main/iso/titan-v7.0.3-singularity.iso`" of=/dev/sdX bs=4M status=progress && sync" "Yellow"
    Write-ColorOutput ""
    Write-ColorOutput "3. VirtualBox:" "White"
    Write-ColorOutput "   - Create new VM" "Yellow"
    Write-ColorOutput "   - Settings > Storage > Controller: IDE" "Yellow"
    Write-ColorOutput "   - Add Optical Drive: $ISOFile" "Yellow"
    Write-ColorOutput ""
} else {
    Write-ColorOutput "[!] ERROR: ISO file not found" "Red"
    Write-ColorOutput "  Check build logs in container output above" "Yellow"
    exit 1
}

Write-ColorOutput ""
Write-ColorOutput "TITAN V8.1 Docker Desktop build complete!" "Green"
