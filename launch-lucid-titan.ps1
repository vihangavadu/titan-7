# Lucid Titan VM Launch Script
# This script launches the Lucid Titan v5 VM using QEMU

$QEMU_PATH = ".\qemu\qemu-system-x86_64.exe"
$QCOW2_IMAGE = "C:\Users\Administrator\Downloads\New folder\Lucid-Titan-v5-RC1\lucid-titan-v5-final.qcow2"

# VM Configuration
$RAM = "4G"              # 4GB RAM (adjust as needed)
$CPU_CORES = "4"         # 4 CPU cores (adjust as needed)
$DISPLAY = "gtk"         # Display type (gtk, sdl, vnc)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Lucid Titan v5 VM Launcher" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Image: $QCOW2_IMAGE"
Write-Host "  RAM: $RAM"
Write-Host "  CPU Cores: $CPU_CORES"
Write-Host "  Display: $DISPLAY"
Write-Host ""
Write-Host "Starting VM..." -ForegroundColor Green
Write-Host ""

# Launch QEMU with the QCOW2 image
& $QEMU_PATH `
    -m $RAM `
    -smp $CPU_CORES `
    -hda $QCOW2_IMAGE `
    -boot c `
    -display $DISPLAY `
    -enable-kvm `
    -cpu host `
    -vga virtio `
    -device virtio-net,netdev=net0 `
    -netdev user,id=net0 `
    -rtc base=localtime `
    -name "Lucid Titan v5"

Write-Host ""
Write-Host "VM has been closed." -ForegroundColor Yellow
