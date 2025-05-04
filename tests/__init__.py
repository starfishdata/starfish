import os
import sys

# Add workspace folders to PYTHONPATH
workspace_folders = [os.path.join(os.path.dirname(__file__), "..", "src"), os.path.dirname(os.path.dirname(__file__))]

for folder in workspace_folders:
    if folder not in sys.path:
        sys.path.insert(0, folder)

# This file is intentionally empty to make the directory a Python package
