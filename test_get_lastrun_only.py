#!/usr/bin/env python3

import tempfile
import os
from oslo_config import cfg
from unittest import mock
import caso.manager
from caso.extract.manager import Manager

# Register all necessary options
CONF = cfg.CONF

# Mock the keystone client to avoid auth issues
with mock.patch('caso.extract.manager.Manager._get_keystone_client'):
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set the spool directory
        CONF.set_override('spooldir', temp_dir)
        
        # Create Manager instance
        manager = Manager()
        
        project_id = "test_project"
        lastrun_file = os.path.join(temp_dir, f"lastrun.{project_id}")
        
        # Test 1: Empty file (this should reproduce the issue)
        print("=== Test 1: Empty file ===")
        with open(lastrun_file, 'w') as f:
            f.write("")  # Empty file
        
        print(f"File exists: {os.path.exists(lastrun_file)}")
        print(f"File content: '{open(lastrun_file).read()}'")
        
        try:
            result = manager.get_lastrun(project_id)
            print(f"Success! Got: {result}")
        except Exception as e:
            print(f"Error occurred: {type(e).__name__}: {e}")
        
        # Test 2: File with only whitespace
        print("\n=== Test 2: File with whitespace only ===")
        with open(lastrun_file, 'w') as f:
            f.write("   \n\t  ")  # Just whitespace
        
        print(f"File content: '{open(lastrun_file).read()}'")
        
        try:
            result = manager.get_lastrun(project_id)
            print(f"Success! Got: {result}")
        except Exception as e:
            print(f"Error occurred: {type(e).__name__}: {e}")
        
        # Test 3: Valid date (should work)
        print("\n=== Test 3: Valid date ===")
        with open(lastrun_file, 'w') as f:
            f.write("2023-01-01")
        
        print(f"File content: '{open(lastrun_file).read()}'")
        
        try:
            result = manager.get_lastrun(project_id)
            print(f"Success! Got: {result}")
        except Exception as e:
            print(f"Error occurred: {type(e).__name__}: {e}")

        # Test 4: No file (should use default)
        print("\n=== Test 4: No file ===")
        os.remove(lastrun_file)
        
        try:
            result = manager.get_lastrun(project_id)
            print(f"Success! Got: {result}")
        except Exception as e:
            print(f"Error occurred: {type(e).__name__}: {e}")
