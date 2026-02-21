#!/usr/bin/env python3
"""
Quick verification script for the multi-provider LLM bridge.
Tests config loading, provider status, and task routing without making actual API calls.
"""

import sys
import os
from pathlib import Path

# Add current dir to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all required functions can be imported."""
    try:
        from ollama_bridge import (
            get_provider_status, resolve_provider_for_task, is_ollama_available,
            get_config, reload_config, get_cache_stats
        )
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_config_loading():
    """Test config file loading."""
    try:
        from ollama_bridge import get_config, reload_config
        
        # Force reload config
        reload_config()
        cfg = get_config()
        
        # Check required sections
        required_sections = ["providers", "task_routing", "cache", "global"]
        for section in required_sections:
            if section not in cfg:
                print(f"❌ Missing config section: {section}")
                return False
        
        print("✅ Config loaded successfully")
        print(f"   - Found {len(cfg['providers'])} providers")
        print(f"   - Found {len(cfg['task_routing'])} task types")
        return True
    except Exception as e:
        print(f"❌ Config loading failed: {e}")
        return False

def test_provider_status():
    """Test provider status checking."""
    try:
        from ollama_bridge import get_provider_status
        
        status = get_provider_status()
        print("✅ Provider status check:")
        for prov, info in status.items():
            enabled = info["enabled"]
            has_key = info["has_api_key"]
            available = info["available"]
            print(f"   - {prov}: enabled={enabled}, has_key={has_key}, available={available}")
        
        return True
    except Exception as e:
        print(f"❌ Provider status check failed: {e}")
        return False

def test_task_routing():
    """Test task routing resolution."""
    try:
        from ollama_bridge import resolve_provider_for_task
        
        task_types = [
            "bin_generation", "site_discovery", "preset_generation",
            "country_profiles", "dork_generation", "warmup_searches", "default"
        ]
        
        print("✅ Task routing resolution:")
        for task in task_types:
            resolved = resolve_provider_for_task(task)
            if resolved:
                prov, model = resolved
                print(f"   - {task}: {prov}/{model}")
            else:
                print(f"   - {task}: No available provider")
        
        return True
    except Exception as e:
        print(f"❌ Task routing failed: {e}")
        return False

def test_dynamic_data_integration():
    """Test that dynamic_data.py can import and use the bridge."""
    try:
        from dynamic_data import LLM_AVAILABLE, OLLAMA_AVAILABLE
        
        print(f"✅ Dynamic data integration:")
        print(f"   - LLM_AVAILABLE: {LLM_AVAILABLE}")
        print(f"   - OLLAMA_AVAILABLE (compat): {OLLAMA_AVAILABLE}")
        
        if LLM_AVAILABLE:
            from dynamic_data import generate_merchant_sites
            print("   - generate_merchant_sites function imported successfully")
        
        return True
    except Exception as e:
        print(f"❌ Dynamic data integration failed: {e}")
        return False

def main():
    """Run all verification tests."""
    print("=== TITAN Multi-Provider LLM Bridge Verification ===\n")
    
    tests = [
        ("Imports", test_imports),
        ("Config Loading", test_config_loading),
        ("Provider Status", test_provider_status),
        ("Task Routing", test_task_routing),
        ("Dynamic Data Integration", test_dynamic_data_integration),
    ]
    
    passed = 0
    total = len(tests)
    
    for name, test_fn in tests:
        print(f"\n--- {name} ---")
        if test_fn():
            passed += 1
        else:
            print(f"Test failed: {name}")
    
    print(f"\n=== Results: {passed}/{total} tests passed ===")
    
    if passed == total:
        print("🎉 All verification tests passed! The multi-provider LLM bridge is working correctly.")
        return 0
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
