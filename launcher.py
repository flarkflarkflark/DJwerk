import sys
import os
import subprocess

# Zorg dat we in de juiste map zitten
os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("--- DJwerk Debug Launcher ---")
print("Starting app and redirecting output to debug.log...")

# Open het logbestand
with open("debug.log", "w") as log_file:
    # Start de main app en stuur alle output (stdout en stderr) naar de log
    process = subprocess.Popen(
        [sys.executable, "main.py"],
        stdout=log_file,
        stderr=log_file,
        bufsize=1,
        universal_newlines=True
    )
    
    print(f"App started with PID: {process.pid}")
    print("I am now monitoring debug.log for you. Go ahead and test!")
    
    try:
        process.wait()
    except KeyboardInterrupt:
        process.terminate()
        print("
Launcher stopped.")
