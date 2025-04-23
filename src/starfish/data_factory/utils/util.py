def is_jupyter_notebook() -> bool:
    """Check if the code is running in a Jupyter notebook."""
    try:
        # Check for IPython kernel
        from IPython import get_ipython

        shell = get_ipython().__class__.__name__
        if shell == "ZMQInteractiveShell":  # Jupyter notebook or qtconsole
            return True
        elif shell == "TerminalInteractiveShell":  # Terminal IPython
            return False
        else:
            return False  # Other type
    except:
        return False  # Probably standard Python interpreter
