import sys
import os

# Zorg dat de huidige map in het pad staat
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from djwerk_gui import DJwerkApp
from djwerk_core import DJwerkCore
from djwerk_controller import DJwerkController

if __name__ == "__main__":
    # Boot de core engine
    core_engine = DJwerkCore()
    
    # Boot de UI
    app = DJwerkApp(core_engine)
    
    # Koppel de controller (deze neemt het stuur over)
    controller = DJwerkController(app)
    
    def on_closing():
        print("[SYSTEM] Shutting down DJwerk...")
        # Forceer exit van alle threads
        os._exit(0)

    app.protocol("WM_DELETE_WINDOW", on_closing)

    # Start de loop
    app.mainloop()
