# You might also include the package version here
# This is often automatically managed by build tools like setuptools_scm
try:
    from importlib.metadata import PackageNotFoundError, version

    try:
        __version__ = version("starfish-core")  # Updated to match our package name
    except PackageNotFoundError:
        # package is not installed
        __version__ = "unknown"
except ImportError:
    # Fallback for older Python versions
    __version__ = "unknown"
