#!/usr/bin/env python3

import tempfile
import os
from oslo_config import cfg
import caso.manager
from caso.extract.manager import Manager

# Register all necessary options
CONF = cfg.CONF

# Create a temp directory for testing
with tempfile.TemporaryDirectory() as temp_dir:
    # Set the spool directory
    CONF.set_override('spooldir', temp_dir)
    
    # Create an empty lastrun file
    project_id = "test_project"
    lastrun_file = os.path.join(temp_dir, f"lastrun.{project_id}")
    
    # Create empty file (this simulates the issue)
    with open(lastrun_file, 'w') as f:
        f.write("")  # Empty file
    
    print(f"Created empty lastrun file: {lastrun_file}")
    print(f"File exists: {os.path.exists(lastrun_file)}")
    print(f"File size: {os.path.getsize(lastrun_file)}")
    
    # Try to reproduce the issue
    try:
        manager = Manager()
        result = manager.get_lastrun(project_id)
        print(f"Success! Got: {result}")
    except Exception as e:
        print(f"Error occurred: {type(e).__name__}: {e}")
