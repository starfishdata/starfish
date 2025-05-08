import pytest
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def pytest_configure(config):
    """Configure pytest for notebook testing."""
    # Register the notebook marker
    config.addinivalue_line("markers", "notebook: mark test as a notebook test")


@pytest.fixture(scope="session")
def notebook_tempdir(tmpdir_factory):
    """Create a temporary directory for notebook execution."""
    return tmpdir_factory.mktemp("notebook_tests")
