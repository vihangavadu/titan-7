#!/usr/bin/env python3
"""
LUCID EMPIRE :: Kernel Module Validator
Tests that hardware masking works correctly via kernel module
"""

import os
import sys
import subprocess
import tempfile

class KernelModuleValidator:
    """Validates kernel-level hardware masking"""
    
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.profile_dir = "/opt/lucid-empire/profiles/active"
    
    def print_header(self, text):
        print(f"\n{'='*60}")
        print(f"  {text}")
        print('='*60)
    
    def print_test(self, name, passed, details=""):
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
        if details:
            print(f"       {details}")
        if passed:
            self.tests_passed += 1
        else:
            self.tests_failed += 1
    
    def check_kernel_module_loaded(self):
        """Verify titan_hw kernel module is loaded"""
        self.print_header("Kernel Module Status")
        try:
            result = subprocess.run(['lsmod'], capture_output=True, text=True)
            is_loaded = 'titan_hw' in result.stdout
            self.print_test(
                "Kernel module loaded",
                is_loaded,
                "Module titan_hw found in lsmod" if is_loaded else "Module NOT loaded"
            )
            return is_loaded
        except Exception as e:
            self.print_test("Kernel module loaded", False, str(e))
            return False
    
    def check_no_ld_preload(self):
        """Verify LD_PRELOAD is not set"""
        self.print_header("Zero-Detect Validation")
        ld_preload = os.environ.get('LD_PRELOAD', '')
        passed = len(ld_preload) == 0
        self.print_test(
            "LD_PRELOAD not set",
            passed,
            f"Value: '{ld_preload}'" if ld_preload else "Clean environment"
        )
        return passed
    
    def check_proc_maps_clean(self):
        """Verify /proc/self/maps doesn't contain userspace hooks"""
        try:
            with open('/proc/self/maps', 'r') as f:
                maps_content = f.read()
            
            # Check for suspicious libraries
            suspicious = ['hardware_shield', 'libhardwareshield']
            found_suspicious = [s for s in suspicious if s in maps_content]
            
            passed = len(found_suspicious) == 0
            self.print_test(
                "Memory maps clean",
                passed,
                "No userspace hooks detected" if passed else f"Found: {found_suspicious}"
            )
            return passed
        except Exception as e:
            self.print_test("Memory maps clean", False, str(e))
            return False
    
    def check_cpuinfo_spoofed(self):
        """Verify /proc/cpuinfo returns spoofed data"""
        self.print_header("Hardware Masking Tests")
        
        try:
            # Read actual cpuinfo
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
            
            # Read expected spoofed data
            spoof_file = os.path.join(self.profile_dir, 'cpuinfo')
            if not os.path.exists(spoof_file):
                self.print_test(
                    "CPU info spoofed",
                    False,
                    f"Profile not found: {spoof_file}"
                )
                return False
            
            with open(spoof_file, 'r') as f:
                expected = f.read()
            
            # Check if they match (at least partially)
            model_name_actual = [l for l in cpuinfo.split('\n') if 'model name' in l]
            model_name_expected = [l for l in expected.split('\n') if 'model name' in l]
            
            if model_name_actual and model_name_expected:
                passed = model_name_actual[0] == model_name_expected[0]
                self.print_test(
                    "CPU info spoofed",
                    passed,
                    f"Expected: {model_name_expected[0][:50]}..." if not passed else "Model name matches profile"
                )
                return passed
            else:
                self.print_test("CPU info spoofed", False, "Could not parse model name")
                return False
                
        except Exception as e:
            self.print_test("CPU info spoofed", False, str(e))
            return False
    
    def test_static_binary_compatibility(self):
        """Test if a static binary sees spoofed hardware"""
        self.print_header("Static Binary Compatibility")
        
        # Create simple C program to read cpuinfo
        c_code = '''
#include <stdio.h>
#include <stdlib.h>

int main() {
    FILE *f = fopen("/proc/cpuinfo", "r");
    if (!f) {
        perror("fopen");
        return 1;
    }
    
    char line[256];
    while (fgets(line, sizeof(line), f)) {
        if (strstr(line, "model name")) {
            printf("%s", line);
            break;
        }
    }
    
    fclose(f);
    return 0;
}
'''
        
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                src_file = os.path.join(tmpdir, 'test.c')
                bin_file = os.path.join(tmpdir, 'test_static')
                
                # Write C code
                with open(src_file, 'w') as f:
                    f.write(c_code)
                
                # Compile as static binary
                compile_result = subprocess.run(
                    ['gcc', '-static', '-o', bin_file, src_file],
                    capture_output=True,
                    text=True
                )
                
                if compile_result.returncode != 0:
                    self.print_test(
                        "Static binary test",
                        False,
                        "Compilation failed (gcc may not be available)"
                    )
                    return False
                
                # Run static binary
                run_result = subprocess.run(
                    [bin_file],
                    capture_output=True,
                    text=True
                )
                
                # Get expected model name
                spoof_file = os.path.join(self.profile_dir, 'cpuinfo')
                with open(spoof_file, 'r') as f:
                    expected_lines = [l for l in f.readlines() if 'model name' in l]
                
                if expected_lines and run_result.stdout:
                    passed = expected_lines[0].strip() == run_result.stdout.strip()
                    self.print_test(
                        "Static binary sees spoofed data",
                        passed,
                        "Static binary correctly reads masked hardware" if passed else "Static binary sees real hardware!"
                    )
                    return passed
                else:
                    self.print_test("Static binary test", False, "No output from binary")
                    return False
                    
        except Exception as e:
            self.print_test("Static binary test", False, f"Test error: {e}")
            return False
    
    def run_all_tests(self):
        """Run complete validation suite"""
        print("\n" + "="*60)
        print("  LUCID EMPIRE - Kernel Module Validation Suite")
        print("="*60)
        
        # Critical tests
        module_loaded = self.check_kernel_module_loaded()
        self.check_no_ld_preload()
        self.check_proc_maps_clean()
        
        if module_loaded:
            self.check_cpuinfo_spoofed()
            self.test_static_binary_compatibility()
        else:
            print("\n⚠ Kernel module not loaded - skipping hardware masking tests")
            print("  Load module with: sudo systemctl start lucid-titan.service")
        
        # Summary
        self.print_header("Test Summary")
        total = self.tests_passed + self.tests_failed
        print(f"Tests Passed: {self.tests_passed}/{total}")
        print(f"Tests Failed: {self.tests_failed}/{total}")
        
        if self.tests_failed == 0:
            print("\n✓ ALL TESTS PASSED - Kernel masking operational")
            return 0
        else:
            print(f"\n✗ {self.tests_failed} TEST(S) FAILED")
            return 1


def main():
    validator = KernelModuleValidator()
    exit_code = validator.run_all_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
