import os


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


# def is_jupyter_notebook() -> bool:
#     """Check if the code is running in a Jupyter notebook."""
#     try:
#         # Check for IPython kernel
#         from IPython import get_ipython
#         from starfish.common.logger import get_logger
#         logger = get_logger(__name__)

#         shell = get_ipython().__class__.__name__
#         if shell == "ZMQInteractiveShell":  # Jupyter notebook or qtconsole
#             logger.info("probably jupyter notebook")
#             return True
#         elif shell == "TerminalInteractiveShell":  # Terminal IPython
#             return False
#         elif shell == "Shell":  # Google Colab
#             logger.info("probably google colab")
#             return True
#         else:
#             return False  # Other type
#     except:
#         return False  # Probably standard Python interpreter


# from IPython import get_ipython
# shell = get_ipython().__class__.__name__
