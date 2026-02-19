#!/bin/bash
# LUCID TITAN :: KYC INJECTOR WRAPPER

# 1. Unload existing module if present
modprobe -r v4l2loopback

# 2. Load with specific capability spoofing
# exclusive_caps=1 makes Chrome/Firefox think it's a real hardware webcam
modprobe v4l2loopback video_nr=0 card_label="Integrated Camera" exclusive_caps=1

# 3. Verify
if [ -e /dev/video0 ]; then
    echo "SUCCESS: Virtual Camera /dev/video0 active."
    echo "Device Name: Integrated Camera"
else
    echo "ERROR: Failed to load kernel module."
    exit 1
fi
