@echo off
echo ========================================
echo   Lucid Titan v5 VM Launcher
echo ========================================
echo.
echo Starting VM with 4GB RAM, 4 CPU cores...
echo.

.\qemu\qemu-system-x86_64.exe ^
    -m 4G ^
    -smp 4 ^
    -hda "C:\Users\Administrator\Downloads\New folder\Lucid-Titan-v5-RC1\lucid-titan-v5-final.qcow2" ^
    -boot c ^
    -display gtk ^
    -vga virtio ^
    -device virtio-net,netdev=net0 ^
    -netdev user,id=net0 ^
    -rtc base=localtime ^
    -name "Lucid Titan v5"

echo.
echo VM has been closed.
pause
