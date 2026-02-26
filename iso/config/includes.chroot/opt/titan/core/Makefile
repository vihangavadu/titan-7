# TITAN V6.2 SOVEREIGN - Kernel Module Build System
# Builds: hardware_shield_v6.ko (procfs/sysfs hardware spoofing)

KDIR ?= /lib/modules/$(shell uname -r)/build
PWD := $(shell pwd)

# Kernel module target
obj-m += hardware_shield_v6.o

# Install paths
INSTALL_DIR := /opt/lucid-empire/hardware_shield
MODULE_NAME := titan_hw

all: module

module:
	$(MAKE) -C $(KDIR) M=$(PWD) modules

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean

install: module
	@mkdir -p $(INSTALL_DIR)
	@mkdir -p /opt/lucid-empire/kernel-modules
	cp hardware_shield_v6.ko $(INSTALL_DIR)/$(MODULE_NAME).ko
	cp hardware_shield_v6.ko /opt/lucid-empire/kernel-modules/$(MODULE_NAME).ko
	@echo "TITAN Hardware Shield installed to $(INSTALL_DIR)/$(MODULE_NAME).ko"

load: install
	@rmmod $(MODULE_NAME) 2>/dev/null || true
	insmod $(INSTALL_DIR)/$(MODULE_NAME).ko
	@echo "TITAN Hardware Shield loaded"
	@dmesg | tail -3

unload:
	@rmmod $(MODULE_NAME) 2>/dev/null || true
	@echo "TITAN Hardware Shield unloaded"

status:
	@if lsmod | grep -q $(MODULE_NAME); then \
		echo "TITAN Hardware Shield: LOADED"; \
		dmesg | grep TITAN-HW-V6 | tail -5; \
	else \
		echo "TITAN Hardware Shield: NOT LOADED"; \
	fi

.PHONY: all module clean install load unload status
