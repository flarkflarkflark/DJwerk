import time
import os
import threading
from unittest.mock import MagicMock
from djwerk_core import DJwerkCore
from djwerk_controller import DJwerkController
from djwerk_matcher import UniversalMatcher

class HeadlessView(MagicMock):
    """A mock view that prints logs to the console instead of a GUI."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fx_enabled = False
        self.cookies_browser = "firefox" # Pas aan naar jouw browser: chrome/firefox/etc.
        self.url_entry = MagicMock()
        self.sync_btn = MagicMock()
        
    def log_message(self, text):
        print(text)
    
    def get_last_log_line(self):
        return ""
        
    def replace_last_log_line(self, text):
        # In headless mode printen we gewoon alles onder elkaar
        print(text)

    def show_track_selector(self, tracks, on_confirm):
        print(f"\n[HEADLESS] Selector opened with {len(tracks)} tracks.")
        print("[HEADLESS] Automatically selecting ALL tracks for headless test...")
        on_confirm(tracks)

    def after(self, ms, func, *args):
        # Simulatie van Tkinter's mainloop delay
        pass

def run_headless_sync(target):
    print(f"--- [HEADLESS SYNC START] Target: {target} ---")
    core = DJwerkCore()
    view = HeadlessView()
    controller = DJwerkController(view)
    
    # YOLO TEXT SYNC: Als de target een bestaand bestand is
    if os.path.exists(target):
        print(f"[HEADLESS] Local file detected: {target}. Reading tracks...")
        with open(target, 'r') as f:
            raw_content = f.read()
        
        # Gebruik de UniversalMatcher om de tekst te ontleden
        tracks_to_process = controller.matcher.get_tracks(raw_content)
        if tracks_to_process:
            print(f"[HEADLESS] Extracted {len(tracks_to_process)} tracks from file.")
            controller.start_selected_sync(tracks_to_process)
        else:
            print("[HEADLESS] ERROR: Could not extract any tracks from file.")
    else:
        # Normale URL sync
        controller._process_sync_thread(target)
    
    # Omdat start_selected_sync in een thread draait, moeten we wachten tot hij klaar is
    while controller.status != "Idle":
        time.sleep(1)
        
    print("--- [HEADLESS SYNC FINISHED] ---")

if __name__ == "__main__":
    import sys
    # Gebruik de URL van de playlist (hier als voorbeeld een korte voor de test, 
    # maar je kunt de 511-url hier plakken)
    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC"
    run_headless_sync(test_url)
