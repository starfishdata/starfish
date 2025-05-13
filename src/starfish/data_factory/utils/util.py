import os
import re
import json
import aiofiles
from typing import List, Dict, Any


def get_platform_name() -> str:
    """Check if the code is running in a Jupyter notebook."""
    try:
        # Check for IPython kernel
        from IPython import get_ipython

        ipython = get_ipython()

        # If not in an interactive environment
        if ipython is None:
            return "PythonShell"

        shell = ipython.__class__.__name__

        # Direct check for Google Colab
        try:
            import google.colab

            shell = "GoogleColabShell"
        except ImportError:
            # Check for VS Code specific environment variables
            if "VSCODE_PID" in os.environ or "VSCODE_CWD" in os.environ:
                shell = "VSCodeShell"
        return shell

    except:
        return "PythonShell"  # Probably standard Python interpreter
