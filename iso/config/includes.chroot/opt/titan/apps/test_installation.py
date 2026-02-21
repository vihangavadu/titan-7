#!/usr/bin/env python3
"""
TITAN Development Hub - Installation Test
Verifies that all components are working correctly
"""

import sys
import os
import json
import importlib
from pathlib import Path

def test_python_version():
    """Test Python version compatibility"""
    print("Testing Python version...")
    
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print(f"❌ Python {version.major}.{version.minor} is too old (need 3.7+)")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True

def test_dependencies():
    """Test required dependencies"""
    print("\nTesting dependencies...")
    
    required_modules = [
        'json',
        'pathlib',
        'threading',
        'subprocess',
        'datetime',
        'uuid',
        'hashlib',
        'time',
        'dataclasses',
        'collections',
        'typing'
    ]
    
    optional_modules = [
        'tkinter',
        'requests',
        'git',
        'numpy',
        'pandas'
    ]
    
    all_good = True
    
    print("Required modules:")
    for module in required_modules:
        try:
            importlib.import_module(module)
            print(f"  ✅ {module}")
        except ImportError:
            print(f"  ❌ {module} - MISSING")
            all_good = False
    
    print("\nOptional modules:")
    for module in optional_modules:
        try:
            importlib.import_module(module)
            print(f"  ✅ {module}")
        except ImportError:
            print(f"  ⚠️  {module} - not installed (optional)")
    
    return all_good

def test_file_structure():
    """Test file structure"""
    print("\nTesting file structure...")
    
    base_path = Path(__file__).parent
    required_files = [
        'titan_dev_hub.py',
        'requirements.txt',
        'launch_dev_hub.sh',
        'launch_dev_hub.bat',
        'README_DevHub.md'
    ]
    
    required_dirs = [
        '../config',
        '../core',
        '../sessions'
    ]
    
    all_good = True
    
    print("Required files:")
    for file_name in required_files:
        file_path = base_path / file_name
        if file_path.exists():
            print(f"  ✅ {file_name}")
        else:
            print(f"  ❌ {file_name} - MISSING")
            all_good = False
    
    print("\nRequired directories:")
    for dir_name in required_dirs:
        dir_path = base_path / dir_name
        if dir_path.exists():
            print(f"  ✅ {dir_name}")
        else:
            print(f"  ⚠️  {dir_name} - will be created automatically")
    
    return all_good

def test_config():
    """Test configuration file"""
    print("\nTesting configuration...")
    
    config_path = Path(__file__).parent.parent / "config" / "dev_hub_config.json"
    
    if not config_path.exists():
        print("❌ Configuration file not found")
        return False
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        required_sections = ['ai', 'git', 'ui', 'features', 'titan']
        
        for section in required_sections:
            if section in config:
                print(f"  ✅ {section} section")
            else:
                print(f"  ❌ {section} section - MISSING")
                return False
        
        print("✅ Configuration file is valid")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Configuration file has invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading configuration: {e}")
        return False

def test_gui():
    """Test GUI availability"""
    print("\nTesting GUI availability...")
    
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()  # Hide the window
        root.destroy()
        print("✅ GUI (tkinter) is available")
        return True
    except ImportError:
        print("❌ GUI (tkinter) is not available")
        return False
    except Exception as e:
        print(f"⚠️  GUI test failed: {e}")
        return False

def test_git():
    """Test Git availability"""
    print("\nTesting Git...")
    
    import subprocess
    
    try:
        result = subprocess.run(
            ['git', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print(f"✅ Git: {result.stdout.strip()}")
            return True
        else:
            print("❌ Git not working")
            return False
            
    except FileNotFoundError:
        print("❌ Git not installed")
        return False
    except Exception as e:
        print(f"⚠️  Git test failed: {e}")
        return False

def test_titan_core():
    """Test TITAN core modules"""
    print("\nTesting TITAN core integration...")
    
    core_path = Path(__file__).parent.parent / "core"
    
    if not core_path.exists():
        print("❌ TITAN core directory not found")
        return False
    
    # Check for key TITAN modules
    key_modules = [
        'cockpit_daemon.py',
        'font_sanitizer.py',
        'forensic_monitor.py',
        'form_autofill_injector.py',
        'generate_trajectory_model.py',
        'handover_protocol.py',
        'integration_bridge.py',
        'intel_monitor.py',
        'location_spoofer_linux.py',
        'lucid_vpn.py'
    ]
    
    found_modules = 0
    for module in key_modules:
        module_path = core_path / module
        if module_path.exists():
            found_modules += 1
    
    print(f"✅ Found {found_modules}/{len(key_modules)} core modules")
    
    if found_modules >= len(key_modules) * 0.8:  # At least 80% of modules
        return True
    else:
        print("⚠️  Some core modules missing - limited functionality")
        return True  # Not a failure, just limited

def test_import_hub():
    """Test importing the main hub"""
    print("\nTesting main hub import...")
    
    try:
        # Add to path if needed
        hub_path = Path(__file__).parent
        if str(hub_path) not in sys.path:
            sys.path.insert(0, str(hub_path))
        
        # Try importing
        import titan_dev_hub
        
        # Test basic instantiation
        hub = titan_dev_hub.TitanDevHub()
        
        print("✅ Main hub imports and initializes correctly")
        return True
        
    except Exception as e:
        print(f"❌ Failed to import hub: {e}")
        return False

def run_all_tests():
    """Run all tests and generate report"""
    print("=" * 60)
    print("TITAN Development Hub - Installation Test")
    print("=" * 60)
    
    tests = [
        ("Python Version", test_python_version),
        ("Dependencies", test_dependencies),
        ("File Structure", test_file_structure),
        ("Configuration", test_config),
        ("GUI Availability", test_gui),
        ("Git", test_git),
        ("TITAN Core", test_titan_core),
        ("Hub Import", test_import_hub)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<30} {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! TITAN Dev Hub is ready to use.")
        print("\nNext steps:")
        print("1. Run: ./launch_dev_hub.sh")
        print("2. Or: python3 titan_dev_hub.py")
        return True
    elif passed >= total * 0.8:
        print("\n⚠️  Most tests passed. You can use the hub with some limitations.")
        print("Check the failed tests above for optional components.")
        return True
    else:
        print("\n❌ Multiple tests failed. Please fix issues before using.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
