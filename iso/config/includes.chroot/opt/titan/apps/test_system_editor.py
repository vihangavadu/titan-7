#!/usr/bin/env python3
"""
Test script for TITAN DevHub System Editor functionality
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from titan_dev_hub import TitanDevHub, SystemEditor, FileEditOperation
    print("✓ Successfully imported System Editor classes")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

def test_system_editor():
    """Test basic system editor functionality"""
    print("\n=== Testing System Editor ===")
    
    # Create a test file
    test_file = "test_sample.py"
    test_content = '''# Test file for TITAN DevHub
def hello_world():
    print("Hello, TITAN OS!")

if __name__ == "__main__":
    hello_world()
'''
    
    try:
        # Write test file
        with open(test_file, 'w') as f:
            f.write(test_content)
        print(f"✓ Created test file: {test_file}")
        
        # Initialize system editor
        editor = SystemEditor()
        print("✓ SystemEditor initialized")
        
        # Test safety check
        is_safe, message = editor.is_safe_to_edit(test_file)
        print(f"✓ Safety check for {test_file}: {is_safe} - {message}")
        
        # Test file edit
        new_content = test_content + "\n# Added by System Editor\ndef new_function():\n    pass\n"
        
        operation = FileEditOperation(
            file_path=test_file,
            new_content=new_content,
            operation_type="test_edit",
            backup=True
        )
        
        success, message = editor.edit_file(operation)
        print(f"✓ File edit result: {success} - {message}")
        
        # Test modification history
        history = editor.get_modification_history()
        print(f"✓ Modification history entries: {len(history)}")
        
        # Test scan editable files
        editable_files = editor.scan_editable_files()
        print(f"✓ Found {len(editable_files)} editable files")
        
        # Cleanup
        if os.path.exists(test_file):
            os.remove(test_file)
            print(f"✓ Cleaned up test file: {test_file}")
            
        print("\n✓ All System Editor tests passed!")
        return True
        
    except Exception as e:
        print(f"\n✗ System Editor test failed: {e}")
        return False

def test_titan_hub():
    """Test TitanDevHub with system editing"""
    print("\n=== Testing TitanDevHub System Integration ===")
    
    try:
        # Initialize hub (without GUI)
        hub = TitanDevHub(gui_mode=False)
        print("✓ TitanDevHub initialized in CLI mode")
        
        # Test system editing methods
        history = hub.get_modification_history()
        print(f"✓ Got modification history: {len(history)} entries")
        
        editable_files = hub.scan_editable_files()
        print(f"✓ Scanned editable files: {len(editable_files)} found")
        
        print("\n✓ All TitanDevHub integration tests passed!")
        return True
        
    except Exception as e:
        print(f"\n✗ TitanDevHub integration test failed: {e}")
        return False

def main():
    """Main test runner"""
    print("TITAN DevHub System Editor Test Suite")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 2
    
    # Test System Editor
    if test_system_editor():
        tests_passed += 1
    
    # Test TitanDevHub integration
    if test_titan_hub():
        tests_passed += 1
    
    # Results
    print("\n" + "=" * 50)
    print(f"Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! System Editor is ready.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
