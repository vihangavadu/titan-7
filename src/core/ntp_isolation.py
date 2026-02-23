"""
Isolation Manager: Complete NTP and time synchronization severance.
Implements service shutdown, registry modification, and firewall rules.
"""
import subprocess
import ctypes
import logging
import platform

try:
    import winreg
except ImportError:
    winreg = None
from typing import Optional, List, Dict, Any
import json
import os


class IsolationManager:
    """
    Manages complete temporal isolation by severing all NTP connections.
    Implements multi-layer isolation: service, registry, firewall, and hypervisor.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize Isolation Manager."""
        self.logger = logger or logging.getLogger(__name__)
        self.isolation_state = {
            'w32time_original': None,
            'registry_original': {},
            'firewall_rules': [],
            'hypervisor_sync': None
        }
        self.state_file = "isolation_state.json"
    
    def enable_isolation(self) -> bool:
        """
        Enable complete NTP isolation.
        
        Returns:
            bool: Success status
        """
        try:
            self.logger.info("Initiating temporal isolation sequence")
            
            # Step 1: Disable W32Time service
            if not self._disable_w32time():
                return False
            
            # Step 2: Modify registry for NTP disable
            if not self._disable_ntp_registry():
                return False
            
            # Step 3: Create firewall rules
            if not self._create_firewall_rules():
                return False
            
            # Step 4: Disable hypervisor time sync
            if not self._disable_hypervisor_sync():
                return False
            
            # Save state for restoration
            self._save_state()
            
            self.logger.info("Temporal isolation complete")
            return True
            
        except Exception as e:
            self.logger.error(f"Isolation failed: {e}")
            return False
    
    def _disable_w32time(self) -> bool:
        """Disable Windows Time service."""
        try:
            # Get current service state
            result = subprocess.run(
                ['sc', 'query', 'w32time'],
                capture_output=True, text=True
            )
            self.isolation_state['w32time_original'] = 'running' if 'RUNNING' in result.stdout else 'stopped'
            
            # Stop the service
            subprocess.run(['net', 'stop', 'w32time'], 
                         capture_output=True, check=False)
            
            # Disable service startup
            result = subprocess.run(
                ['sc', 'config', 'w32time', 'start=', 'disabled'],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                self.logger.info("W32Time service disabled")
                return True
            else:
                self.logger.error(f"Failed to disable W32Time: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"W32Time disable error: {e}")
            return False
    
    def _disable_ntp_registry(self) -> bool:
        """Modify registry to disable NTP synchronization."""
        try:
            key_path = r"SYSTEM\CurrentControlSet\Services\W32Time\Parameters"
            
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 
                               0, winreg.KEY_ALL_ACCESS) as key:
                
                # Save original values
                try:
                    original_type, _ = winreg.QueryValueEx(key, "Type")
                    self.isolation_state['registry_original']['Type'] = original_type
                except:
                    pass
                
                try:
                    original_server, _ = winreg.QueryValueEx(key, "NtpServer")
                    self.isolation_state['registry_original']['NtpServer'] = original_server
                except:
                    pass
                
                # Set Type to NoSync
                winreg.SetValueEx(key, "Type", 0, winreg.REG_SZ, "NoSync")
                
                # Clear NTP server
                winreg.SetValueEx(key, "NtpServer", 0, winreg.REG_SZ, "")
                
            self.logger.info("Registry NTP settings disabled")
            return True
            
        except Exception as e:
            self.logger.error(f"Registry modification failed: {e}")
            return False
    
    def _create_firewall_rules(self) -> bool:
        """Create Windows Firewall rules to block NTP traffic."""
        try:
            rules = [
                {
                    'name': 'PROMETHEUS_Block_NTP_Out',
                    'direction': 'out',
                    'protocol': 'UDP',
                    'port': '123',
                    'action': 'block'
                },
                {
                    'name': 'PROMETHEUS_Block_NTP_In',
                    'direction': 'in',
                    'protocol': 'UDP',
                    'port': '123',
                    'action': 'block'
                }
            ]
            
            for rule in rules:
                cmd = [
                    'netsh', 'advfirewall', 'firewall', 'add', 'rule',
                    f'name={rule["name"]}',
                    f'dir={rule["direction"]}',
                    f'protocol={rule["protocol"]}',
                    f'localport={rule["port"]}' if rule["direction"] == "in" else f'remoteport={rule["port"]}',
                    f'action={rule["action"]}'
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    self.isolation_state['firewall_rules'].append(rule['name'])
                    self.logger.info(f"Firewall rule created: {rule['name']}")
                else:
                    self.logger.warning(f"Firewall rule creation failed: {result.stderr}")
            
            return len(self.isolation_state['firewall_rules']) > 0
            
        except Exception as e:
            self.logger.error(f"Firewall configuration error: {e}")
            return False
    
    def _disable_hypervisor_sync(self) -> bool:
        """Disable hypervisor time synchronization if in VM."""
        try:
            # Detect virtualization
            vm_type = self._detect_vm()
            
            if not vm_type:
                self.logger.info("No virtualization detected")
                return True
            
            self.logger.info(f"Detected VM type: {vm_type}")
            
            if vm_type == "vmware":
                # VMware time sync disable
                subprocess.run(['vmware-toolbox-cmd', 'timesync', 'disable'],
                             capture_output=True, check=False)
                self.isolation_state['hypervisor_sync'] = 'vmware'
                
            elif vm_type == "virtualbox":
                # VirtualBox time sync disable
                subprocess.run(['VBoxManage', 'setextradata', 'global', 
                              'VBoxInternal/Devices/VMMDev/0/Config/GetHostTimeDisabled', '1'],
                             capture_output=True, check=False)
                self.isolation_state['hypervisor_sync'] = 'virtualbox'
                
            elif vm_type == "hyperv":
                # Hyper-V time sync disable via PowerShell
                ps_cmd = "Disable-VMIntegrationService -Name 'Time Synchronization'"
                subprocess.run(['powershell', '-Command', ps_cmd],
                             capture_output=True, check=False)
                self.isolation_state['hypervisor_sync'] = 'hyperv'
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Hypervisor sync disable warning: {e}")
            return True  # Non-critical, continue
    
    def _detect_vm(self) -> Optional[str]:
        """Detect if running in a virtual machine."""
        try:
            # Check for VM artifacts
            result = subprocess.run(['wmic', 'computersystem', 'get', 'model'],
                                  capture_output=True, text=True)
            
            model = result.stdout.lower()
            
            if 'vmware' in model:
                return 'vmware'
            elif 'virtualbox' in model:
                return 'virtualbox'
            elif 'virtual' in model:
                return 'hyperv'
            
            # Check for VM services
            services = subprocess.run(['sc', 'query'], 
                                    capture_output=True, text=True).stdout.lower()
            
            if 'vmware' in services:
                return 'vmware'
            elif 'vbox' in services:
                return 'virtualbox'
            elif 'vmbus' in services:
                return 'hyperv'
                
        except:
            pass
        
        return None
    
    def verify_isolation(self) -> bool:
        """Verify that isolation is complete."""
        try:
            # Check W32Time is disabled
            result = subprocess.run(['sc', 'query', 'w32time'],
                                  capture_output=True, text=True)
            if 'RUNNING' in result.stdout:
                return False
            
            # Check registry
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                              r"SYSTEM\CurrentControlSet\Services\W32Time\Parameters") as key:
                value, _ = winreg.QueryValueEx(key, "Type")
                if value != "NoSync":
                    return False
            
            # Check firewall rules exist
            result = subprocess.run(['netsh', 'advfirewall', 'firewall', 'show', 'rule', 
                                   'name=PROMETHEUS_Block_NTP_Out'],
                                  capture_output=True, text=True)
            if 'No rules' in result.stdout:
                return False
            
            self.logger.info("Isolation verification successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Isolation verification failed: {e}")
            return False
    
    def disable_isolation(self) -> bool:
        """Disable isolation and restore normal NTP operation."""
        try:
            self.logger.info("Restoring temporal connectivity")
            
            # Load saved state
            self._load_state()
            
            # Restore W32Time service
            if self.isolation_state.get('w32time_original') == 'running':
                subprocess.run(['sc', 'config', 'w32time', 'start=', 'auto'],
                             capture_output=True)
                subprocess.run(['net', 'start', 'w32time'],
                             capture_output=True)
            
            # Restore registry
            if self.isolation_state.get('registry_original'):
                self._restore_registry()
            
            # Remove firewall rules
            for rule_name in self.isolation_state.get('firewall_rules', []):
                subprocess.run(['netsh', 'advfirewall', 'firewall', 'delete', 
                              'rule', f'name={rule_name}'],
                             capture_output=True)
            
            # Restore hypervisor sync
            if self.isolation_state.get('hypervisor_sync'):
                self._restore_hypervisor_sync()
            
            # Force time resync
            subprocess.run(['w32tm', '/resync', '/force'],
                         capture_output=True)
            
            self.logger.info("Temporal connectivity restored")
            return True
            
        except Exception as e:
            self.logger.error(f"Isolation restore failed: {e}")
            return False
    
    def _restore_registry(self):
        """Restore original registry values."""
        try:
            key_path = r"SYSTEM\CurrentControlSet\Services\W32Time\Parameters"
            
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path,
                               0, winreg.KEY_ALL_ACCESS) as key:
                
                if 'Type' in self.isolation_state['registry_original']:
                    winreg.SetValueEx(key, "Type", 0, winreg.REG_SZ,
                                    self.isolation_state['registry_original']['Type'])
                
                if 'NtpServer' in self.isolation_state['registry_original']:
                    winreg.SetValueEx(key, "NtpServer", 0, winreg.REG_SZ,
                                    self.isolation_state['registry_original']['NtpServer'])
        except:
            pass
    
    def _restore_hypervisor_sync(self):
        """Restore hypervisor time synchronization."""
        try:
            vm_type = self.isolation_state.get('hypervisor_sync')
            
            if vm_type == 'vmware':
                subprocess.run(['vmware-toolbox-cmd', 'timesync', 'enable'],
                             capture_output=True)
            elif vm_type == 'virtualbox':
                subprocess.run(['VBoxManage', 'setextradata', 'global',
                              'VBoxInternal/Devices/VMMDev/0/Config/GetHostTimeDisabled', '0'],
                             capture_output=True)
            elif vm_type == 'hyperv':
                ps_cmd = "Enable-VMIntegrationService -Name 'Time Synchronization'"
                subprocess.run(['powershell', '-Command', ps_cmd],
                             capture_output=True)
        except:
            pass
    
    def _save_state(self):
        """Save isolation state to file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.isolation_state, f)
        except:
            pass
    
    def _load_state(self):
        """Load isolation state from file."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    self.isolation_state = json.load(f)
        except:
            pass
    
    def emergency_restore(self):
        """Emergency restoration of all services."""
        try:
            # Force enable W32Time
            subprocess.run(['sc', 'config', 'w32time', 'start=', 'auto'],
                         capture_output=True, timeout=30)
            subprocess.run(['net', 'start', 'w32time'],
                         capture_output=True, timeout=30)
            
            # Remove all PROMETHEUS firewall rules
            subprocess.run(['netsh', 'advfirewall', 'firewall', 'delete', 
                          'rule', 'name=all', 'protocol=udp', 'localport=123'],
                         capture_output=True, timeout=30)
            
            # Force resync
            subprocess.run(['w32tm', '/resync', '/force'],
                         capture_output=True, timeout=30)
            
        except Exception as e:
            self.logger.error(f"Emergency restore failed: {e}")