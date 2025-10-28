# pattern: Functional Core
# Pure functions for CUDA dependency detection and library path management

import os
import sys
import site
from pathlib import Path
from typing import Optional


def find_pytorch_cudnn_path() -> Optional[Path]:
    """Find PyTorch's bundled cuDNN library path.

    PyTorch bundles cuDNN in the nvidia-cudnn-cu12 package, but it's not
    automatically added to the system library path. This function locates
    the bundled cuDNN libraries in both development (venv) and installed
    (RPM/DEB) environments.

    Returns:
        Path to cuDNN lib directory if found, None otherwise
    """
    # List of potential search paths
    search_paths = []

    # 1. Check site-packages (for venv/development installations)
    try:
        search_paths.extend(site.getsitepackages())
    except Exception:
        pass

    # 2. Check bundled installation path (for RPM/DEB packages)
    # When installed via package manager, dependencies are at /usr/lib/talk-it-out
    search_paths.append("/usr/lib/talk-it-out")

    # 3. Check PYTHONPATH entries (fallback)
    pythonpath = os.environ.get("PYTHONPATH", "")
    if pythonpath:
        search_paths.extend(pythonpath.split(":"))

    # Search for cuDNN in all potential locations
    for search_path in search_paths:
        if not search_path:  # Skip empty paths
            continue

        cudnn_lib = Path(search_path) / "nvidia" / "cudnn" / "lib"
        if cudnn_lib.exists() and cudnn_lib.is_dir():
            # Verify it actually contains cuDNN libraries
            if any(cudnn_lib.glob("libcudnn_ops.so*")):
                return cudnn_lib

    return None


def setup_cuda_library_path() -> bool:
    """Setup LD_LIBRARY_PATH to include PyTorch's bundled cuDNN.

    This function must be called VERY EARLY in the application startup, before
    any CUDA libraries are loaded. If LD_LIBRARY_PATH needs to be updated and
    hasn't been set yet, this will re-exec the current process with the updated
    environment to ensure the dynamic linker sees the new path.

    Returns:
        True if cuDNN path was found and configured, False otherwise

    Note:
        This function may call os.execv() to restart the process with updated
        environment. This is necessary because LD_LIBRARY_PATH must be set
        before the dynamic linker runs.
    """
    cudnn_path = find_pytorch_cudnn_path()

    if cudnn_path is None:
        return False

    cudnn_path_str = str(cudnn_path)
    current_ld_path = os.environ.get("LD_LIBRARY_PATH", "")

    # Check if cuDNN path is already in LD_LIBRARY_PATH
    if cudnn_path_str in current_ld_path:
        return True

    # Check if we've already re-exec'd (to prevent infinite loop)
    if os.environ.get("_TALK_IT_OUT_CUDA_SETUP_DONE") == "1":
        # We already tried to re-exec, but something went wrong
        # Just update the env var and hope for the best
        if current_ld_path:
            os.environ["LD_LIBRARY_PATH"] = f"{cudnn_path_str}:{current_ld_path}"
        else:
            os.environ["LD_LIBRARY_PATH"] = cudnn_path_str
        return True

    # Need to re-exec with updated LD_LIBRARY_PATH
    if current_ld_path:
        new_ld_path = f"{cudnn_path_str}:{current_ld_path}"
    else:
        new_ld_path = cudnn_path_str

    # Set the environment variables for the re-exec'd process
    new_env = os.environ.copy()
    new_env["LD_LIBRARY_PATH"] = new_ld_path
    new_env["_TALK_IT_OUT_CUDA_SETUP_DONE"] = "1"

    # Re-exec ourselves with the new environment
    # This ensures the dynamic linker sees the updated LD_LIBRARY_PATH
    os.execve(sys.executable, [sys.executable] + sys.argv, new_env)
