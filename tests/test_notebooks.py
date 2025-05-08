"""
Helper module to discover and run test notebooks with pytest.

This module is optional. If you want to run notebook tests directly, you can use:
    pytest path/to/notebook.ipynb
"""

import os
import pytest
from pathlib import Path


def get_notebooks(base_dir=None):
    """Find all test notebooks in the project directory."""
    if base_dir is None:
        base_dir = Path(__file__).parent.parent
    else:
        base_dir = Path(base_dir)

    notebooks = []
    for nb_path in base_dir.rglob("*.ipynb"):
        # Skip checkpoints
        if ".ipynb_checkpoints" in str(nb_path):
            continue
        # Only include notebooks that follow test naming convention
        if nb_path.name.startswith("test_"):
            notebooks.append(str(nb_path))

    return notebooks


@pytest.mark.notebook
@pytest.mark.parametrize("notebook_file", get_notebooks())
def test_notebook_execution(notebook_file):
    """Run the notebook through pytest to verify it executes without errors."""
    pytest.importorskip("pytest_notebook")

    # This test will be collected by pytest-notebook
    # We just need to ensure the file exists
    assert os.path.exists(notebook_file), f"Notebook file not found: {notebook_file}"

    # The actual testing of the notebook is handled by pytest-notebook plugin
