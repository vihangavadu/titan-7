#!/bin/bash
# TITAN V7.5 SINGULARITY — Initramfs DMI Injection Hook
# Executes BEFORE udev/sysfs population to eliminate the race condition
# where early-executing telemetry scripts capture virtualized signatures.
#
# Installation:
#   cp initramfs_dmi_hook.sh /etc/initramfs-tools/scripts/init-premount/titan-dmi
#   chmod +x /etc/initramfs-tools/scripts/init-premount/titan-dmi
#   update-initramfs -u
#
# This hook runs in the initramfs before the root filesystem is mounted,
# ensuring DMI values are overridden from the earliest possible moment.

PREREQ=""
prereqs()
{
    echo "$PREREQ"
}

case $1 in
    prereqs)
        prereqs
        exit 0
        ;;
esac

# V7.5: Dell XPS 15 9520 profile (matches hardware_shield_v6.c defaults)
TITAN_SYS_VENDOR="Dell Inc."
TITAN_PRODUCT_NAME="XPS 15 9520"
TITAN_BOARD_VENDOR="Dell Inc."
TITAN_BOARD_NAME="0RH1JY"
TITAN_BIOS_VENDOR="Dell Inc."
TITAN_BIOS_VERSION="1.18.0"
TITAN_BIOS_DATE="09/12/2024"
TITAN_CHASSIS_TYPE="10"
TITAN_CHASSIS_VENDOR="Dell Inc."

# Generate random serial and UUID (consistent per boot via machine-id seed)
if [ -f /etc/machine-id ]; then
    SEED=$(cat /etc/machine-id)
else
    SEED=$(cat /proc/sys/kernel/random/boot_id 2>/dev/null || echo "titan-default-seed")
fi

# Derive deterministic serial from seed (same per machine, changes on reinstall)
TITAN_SERIAL=$(echo -n "${SEED}-serial" | md5sum | cut -c1-14 | tr 'a-f' 'A-F')
TITAN_UUID=$(echo -n "${SEED}-uuid" | md5sum | sed 's/\(.\{8\}\)\(.\{4\}\)\(.\{4\}\)\(.\{4\}\)\(.\{12\}\).*/\1-\2-4\3-\4-\5/' | tr 'a-f' 'A-F')

# Override DMI entries via bind mounts (works in initramfs before udev)
override_dmi() {
    local path="$1"
    local value="$2"
    local tmpfile="/run/titan-dmi-$(basename "$path")"

    if [ -f "$path" ]; then
        echo -n "$value" > "$tmpfile"
        mount --bind "$tmpfile" "$path" 2>/dev/null
    fi
}

# Wait for sysfs to be populated
if [ -d /sys/class/dmi/id ]; then
    override_dmi "/sys/class/dmi/id/sys_vendor"      "$TITAN_SYS_VENDOR"
    override_dmi "/sys/class/dmi/id/product_name"     "$TITAN_PRODUCT_NAME"
    override_dmi "/sys/class/dmi/id/board_vendor"     "$TITAN_BOARD_VENDOR"
    override_dmi "/sys/class/dmi/id/board_name"       "$TITAN_BOARD_NAME"
    override_dmi "/sys/class/dmi/id/bios_vendor"      "$TITAN_BIOS_VENDOR"
    override_dmi "/sys/class/dmi/id/bios_version"     "$TITAN_BIOS_VERSION"
    override_dmi "/sys/class/dmi/id/bios_date"        "$TITAN_BIOS_DATE"
    override_dmi "/sys/class/dmi/id/chassis_type"     "$TITAN_CHASSIS_TYPE"
    override_dmi "/sys/class/dmi/id/chassis_vendor"   "$TITAN_CHASSIS_VENDOR"
    override_dmi "/sys/class/dmi/id/product_serial"   "$TITAN_SERIAL"
    override_dmi "/sys/class/dmi/id/product_uuid"     "$TITAN_UUID"
    override_dmi "/sys/class/dmi/id/board_serial"     "$TITAN_SERIAL"
fi

# Suppress /sys/hypervisor if present (KVM/Xen marker)
if [ -d /sys/hypervisor ]; then
    mkdir -p /run/titan-empty-hv
    mount --bind /run/titan-empty-hv /sys/hypervisor 2>/dev/null
fi

# Suppress KVM ACPI WAET table
if [ -f /sys/firmware/acpi/tables/WAET ]; then
    echo -n "" > /run/titan-empty-waet
    mount --bind /run/titan-empty-waet /sys/firmware/acpi/tables/WAET 2>/dev/null
fi

exit 0
