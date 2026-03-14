import os
import platform
import subprocess
import sys
import shutil
from djwerk_version import APP_NAME, APP_VERSION

def run_pyinstaller():
    """Runs PyInstaller using the djwerk.spec file."""
    print(f">> INITIATING MULTI-PLATFORM BUILD PIPELINE ({APP_NAME} v{APP_VERSION})...")
    system = platform.system()
    
    try:
        # Check if pyinstaller is installed in the active environment
        subprocess.run([sys.executable, "-m", "PyInstaller", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[ERROR] PyInstaller not found. Please install it with 'pip install pyinstaller'.")
        sys.exit(1)

    print(f"[INSTALLER] Running PyInstaller on {system}...")

    # Clean old build artifacts to avoid stale binaries.
    for folder in ("build", "dist"):
        if os.path.exists(folder):
            shutil.rmtree(folder, ignore_errors=True)
    
    # Run pyinstaller with the spec file
    result = subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "djwerk.spec"], check=True)
    
    if result.returncode == 0:
        print(f">> BUILD PIPELINE COMPLETE. ARTIFACTS READY IN ./dist")
    else:
        print(f"[ERROR] Build failed with return code {result.returncode}")

if __name__ == "__main__":
    run_pyinstaller()
