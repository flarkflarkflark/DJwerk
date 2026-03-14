import os
import platform
import subprocess
import sys

def run_pyinstaller():
    """Runs PyInstaller using the djwerk.spec file."""
    print(">> INITIATING MULTI-PLATFORM BUILD PIPELINE...")
    system = platform.system()
    
    try:
        # Check if pyinstaller is installed
        subprocess.run(["pyinstaller", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[ERROR] PyInstaller not found. Please install it with 'pip install pyinstaller'.")
        sys.exit(1)

    print(f"[INSTALLER] Running PyInstaller on {system}...")
    
    # Run pyinstaller with the spec file
    result = subprocess.run(["pyinstaller", "--noconfirm", "djwerk.spec"], check=True)
    
    if result.returncode == 0:
        print(f">> BUILD PIPELINE COMPLETE. ARTIFACTS READY IN ./dist")
    else:
        print(f"[ERROR] Build failed with return code {result.returncode}")

if __name__ == "__main__":
    run_pyinstaller()
