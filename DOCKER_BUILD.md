# TITAN V7.0.3 — Docker/WSL Build Guide

**Authority:** Dva.12 | **Status:** OBLIVION_ACTIVE  
**Purpose:** Build Titan ISO using Docker in WSL Ubuntu or Docker Desktop

---

## Prerequisites

### Option 1: Docker Desktop (Recommended for Windows)

1. **Install Docker Desktop for Windows**
   - Download: https://www.docker.com/products/docker-desktop
   - Install with WSL2 backend enabled
   - Start Docker Desktop and wait for full initialization

2. **Enable WSL2 Integration**
   - Docker Desktop Settings > Resources > WSL Integration
   - Enable your Ubuntu distribution
   - Restart Docker Desktop

### Option 2: Docker in WSL Ubuntu

1. **Install Ubuntu from Microsoft Store**
2. **Install Docker in WSL:**
   ```bash
   # In WSL Ubuntu
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER
   # Restart WSL: wsl --shutdown then reopen
   ```

---

## Quick Start (3 Methods)

### Method 1: PowerShell (Docker Desktop) - Easiest

```powershell
# In PowerShell, from titan-main directory
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\build_docker.ps1

# Options:
.\build_docker.ps1 -SkipBuild    # Use existing Docker image
.\build_docker.ps1 -Clean        # Clean Docker environment
.\build_docker.ps1 -Help         # Show help
```

### Method 2: Bash Script (WSL Ubuntu)

```bash
# In WSL Ubuntu, from titan-main directory
cd /mnt/c/Users/Administrator/Desktop/titan-main
chmod +x build_docker.sh
./build_docker.sh
```

### Method 3: Manual Docker Commands

```bash
# Build Docker image
docker build -t titan-build -f Dockerfile.build .

# Run build container
docker run -it --rm \
  -v "$(pwd):/workspace" \
  -v titan-build-cache:/var/cache/apt \
  --cap-add SYS_ADMIN \
  --device /dev/fuse \
  --security-opt apparmor:unconfined \
  titan-build \
  /usr/local/bin/build-titan.sh
```

---

## Build Process

The Docker build process includes:

1. **Environment Check** - Verify Docker, WSL, disk space
2. **Docker Image Build** - Create Debian 12 build environment (5-10 min)
3. **Container Preparation** - Clean previous containers, create cache volume
4. **ISO Build** - Run build_local.sh inside container (30-60 min)
5. **Output Verification** - Check ISO, generate SHA256

### What Happens Inside Container

- Runs `build_local.sh` (5 phases)
- Phase 1: Preflight checks (OS, RAM, disk, dependencies)
- Phase 2: Install missing dependencies
- Phase 3: Run finalization protocol (AI strip, sysctl verify)
- Phase 4: Build ISO via `lb build`
- Phase 5: Post-build verification (checksum, structure)

---

## Expected Output

After successful build:

```
╔══════════════════════════════════════════════════════════════╗
║  BUILD COMPLETE                                             ║
╠══════════════════════════════════════════════════════════════╣
║  ISO:        C:\Users\Administrator\Desktop\titan-main\iso\titan-v7.0.3-singularity.iso
║  Size:       2.4GB
║  SHA256:     C:\Users\Administrator\Desktop\titan-main\iso\titan-v7.0.3-singularity.iso.sha256
╚══════════════════════════════════════════════════════════════╝
```

---

## Testing the ISO

### In QEMU/KVM (Linux/WSL)

```bash
qemu-system-x86_64 \
  -m 4096 \
  -enable-kvm \
  -cdrom iso/titan-v7.0.3-singularity.iso \
  -boot d
```

### In VirtualBox (Windows)

1. Create new VM
2. Settings > Storage > Controller: IDE
3. Add Optical Drive: `titan-v7.0.3-singularity.iso`
4. Start VM

### Write to USB (DESTRUCTIVE)

```bash
# In WSL Ubuntu - BE CAREFUL with device path!
sudo dd if="/mnt/c/Users/Administrator/Desktop/titan-main/iso/titan-v7.0.3-singularity.iso" \
        of=/dev/sdX bs=4M status=progress && sync
```

---

## Troubleshooting

### Docker Issues

**"Docker not found"**
- Install Docker Desktop or Docker in WSL
- Restart PowerShell/WSL after installation

**"Docker not running"**
- Start Docker Desktop
- Or in WSL: `sudo service docker start`

**"permission denied while trying to connect to the Docker daemon socket"**
- In WSL: `sudo usermod -aG docker $USER` then restart WSL
- On Windows: Restart Docker Desktop

### Build Issues

**Container build fails**
- Check available disk space (need 10GB+)
- Ensure Docker Desktop has enough memory allocated (8GB+ recommended)
- Try rebuilding Docker image: `.\build_docker.ps1 -Clean`

**ISO not found after build**
- Check build logs in container output
- Verify `iso/finalize_titan.sh` exists
- Try manual build: `docker run -it --rm -v "$(pwd):/workspace" titan-build bash`

### WSL Issues

**Path not found errors**
- Ensure you're in `titan-main` directory
- Check path: `ls iso/finalize_titan.sh`

**Permission denied**
- In WSL: Make sure your user is in docker group
- On Windows: Run PowerShell as Administrator

---

## Docker Volumes and Caching

The build uses Docker volumes for caching:

- `titan-build-cache`: APT package cache (speeds up subsequent builds)
- `/workspace`: Mounted source directory (your titan-main folder)

To clean up:

```powershell
# PowerShell
.\build_docker.ps1 -Clean

# Or manually
docker volume rm titan-build-cache
docker rmi titan-build:latest
```

---

## Performance Tips

1. **Allocate enough resources to Docker Desktop:**
   - Memory: 8GB+ (recommended)
   - CPUs: 4+ (recommended)
   - Disk: 50GB+ (SSD recommended)

2. **Use SSD storage** for better I/O performance

3. **Enable WSL2 integration** in Docker Desktop settings

4. **Close unnecessary applications** during build (needs 8GB+ RAM)

---

## Security Notes

- The build container runs with elevated privileges (`--cap-add SYS_ADMIN`)
- This is required for `lb build` to work properly
- The container is automatically removed after build (`--rm` flag)
- Build artifacts are only stored in your mounted directory

---

## Advanced Usage

### Custom Docker Build

```bash
# Build with custom tag
docker build -t titan-build:custom -f Dockerfile.build .

# Run with custom parameters
docker run -it --rm \
  -v "$(pwd):/workspace" \
  --memory 8g \
  --cpus 4 \
  titan-build:custom \
  /usr/local/bin/build-titan.sh
```

### Debug Mode

```bash
# Get shell in build container
docker run -it --rm \
  -v "$(pwd):/workspace" \
  titan-build \
  bash

# Inside container:
cd /workspace
./build_local.sh
```

---

## Support

- **Build Guide:** `BUILD_GUIDE.md`
- **Technical Reference:** `TITAN_V703_SINGULARITY.md`
- **Issues:** Check container output for error messages
- **Logs:** Build logs appear in real-time in terminal

---

**Build Status:** Docker Ready  
**WSL Support:** Full  
**Docker Desktop Support:** Full  
**Windows PowerShell Support:** Full  

**Authority:** Dva.12 | **Protocol:** OBLIVION_ACTIVE
