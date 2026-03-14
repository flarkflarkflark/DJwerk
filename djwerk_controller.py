import os
import threading
import time
import re
from typing import Optional
from models.config import THEMES
from djwerk_core import DJwerkCore
from djwerk_matcher import UniversalMatcher
from universal_db import UniversalDBHandler
from rekordbox_xml import RekordboxXMLGenerator
from crate_health import CrateHealthScanner
from engine_integrity import DatabaseValidator

class DJwerkController:
    """The Controller in DJwerk's MVC pattern.

    This class handles the communication between the View (UI) and the logic/models.
    It manages various services like track downloading, metadata matching,
    database handling, and UI-independent tasks without blocking the main thread.
    """

    def __init__(self, view):
        self.view = view
        self.core = DJwerkCore()
        self.matcher = UniversalMatcher()
        self.db_path = "m.db"
        
        self.universal_db = UniversalDBHandler(self.db_path)
        self.rb_xml = RekordboxXMLGenerator("rekordbox.xml")
        self.health_scanner = CrateHealthScanner()

        self.current_bpm = 120.0
        self.status = "Idle"
        self.glow_value = 0
        self.glow_factor = 0.0
        self.glow_direction = 1
        self.current_speed = 0
        self.energy_level = 0.5 # Default energy level

        self.view.sync_btn.configure(command=self.sync_event)
        
        if hasattr(self.view, 'folder_btn'):
            self.view.folder_btn.configure(command=self.open_downloads_folder)
        elif hasattr(self.view, 'downloads_btn'):
            self.view.downloads_btn.configure(command=self.open_downloads_folder)
            
        if hasattr(self.view, 'health_btn'):
            self.view.health_btn.configure(command=self.scan_health_event)
            
        if hasattr(self.view, 'theme_optionmenu'):
            self.view.theme_optionmenu.configure(command=self.change_theme)
            
        if hasattr(self.view, 'settings_btn'):
            self.view.settings_btn.configure(command=self.settings_event)
        
        if hasattr(self.view, 'log_message'):
            self.initialize_ui_log()
            
        if hasattr(self.view, 'glow_panel'):
            self.animate_glow()
            
        # Luister naar settings updates (om FX aan/uit te kunnen zetten)
        if hasattr(self.view, 'bind'):
            self.view.bind("<<SettingsUpdated>>", lambda e: self._handle_settings_update())

    def initialize_ui_log(self):
        self.view.log_message(">> DJwerk Core: V0.1.0 - The Crate Engine")
        self.view.log_message(">> Universal DB Injector: CONNECTED (Dry-Run Safety Active)")
        self.view.log_message(">> Deep Core Scrapers: INITIALIZED")
        self.view.log_message(">> Awaiting URL Input...")

    def hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def rgb_to_hex(self, rgb):
        return '#%02x%02x%02x' % rgb

    def lerp_color(self, color1, color2, factor):
        rgb1 = self.hex_to_rgb(color1)
        rgb2 = self.hex_to_rgb(color2)
        new_rgb = tuple(int(rgb1[i] + (rgb2[i] - rgb1[i]) * factor) for i in range(3))
        return self.rgb_to_hex(new_rgb)

    def _handle_settings_update(self):
        """Wordt aangeroepen als de user de settings saved. Checkt of FX net is uitgezet."""
        if not getattr(self.view, 'fx_enabled', True):
            # Reset de glow state naar basic
            if hasattr(self.view, 'glow_panel'):
                self.view.glow_panel.configure(fg_color="#0a0a0a")
            if hasattr(self.view, 'visualizer_label'):
                self.view.visualizer_label.configure(text="[ FX DISABLED ]", text_color="#555555")

    def animate_glow(self):
        # Stop de recursie als fx is uitgezet via de GUI
        if not getattr(self.view, 'fx_enabled', True):
            # Check over 1 seconde nog eens (als ze hem weer aanzetten)
            self.view.after(1000, self.animate_glow)
            return

        theme_name = getattr(self.view, 'current_theme_name', "Classic Orange")
        theme = THEMES.get(theme_name, {"accent": "#FF8C00", "bg_glow": "#2b2b2b"})
        accent = theme.get("accent", "#FF8C00")
        bg_glow = theme.get("bg_glow", "#2b2b2b")

        status_colors = {
            "Idle": (bg_glow, "#0a0a0a"),
            "Scanning": ("#000033", "#000099"),
            "Downloading": ("#330000", "#990000"),
            "Syncing": ("#003300", "#009900"),
            "Error": ("#550000", "#ff0000")
        }

        energy_color = self.lerp_color("#0000FF", "#FF0000", self.energy_level)
        c1, c2 = status_colors.get(self.status, status_colors["Idle"])
        
        if self.status in ["Syncing", "Idle"]:
            c2 = self.lerp_color(c2, energy_color, 0.4)

        step = 0.05
        self.glow_factor += step * self.glow_direction
        if self.glow_factor >= 1.0:
            self.glow_factor = 1.0
            self.glow_direction = -1
        elif self.glow_factor <= 0.0:
            self.glow_factor = 0.0
            self.glow_direction = 1

        current_color = self.lerp_color(c1, c2, self.glow_factor)
        
        if hasattr(self.view, 'glow_panel'):
            self.view.glow_panel.configure(fg_color=current_color)
        
        if hasattr(self.view, 'visualizer_label'):
            text_color = accent if self.glow_factor > (1.0 - self.energy_level) else "#ffffff"
            self.view.visualizer_label.configure(text_color=text_color)
            
            visualizer_states = ["[ MILKDROP 3 VIBE ]", "[ GLOW SHADER ACTIVE ]", "[ ENERGY PULSE ]", "[ FLARKING... ]"]
            import random
            if self.glow_factor < 0.1:
                self.view.visualizer_label.configure(text=random.choice(visualizer_states))

        if self.status == "Idle": glow_delay = 150
        elif self.status in ["Scanning", "Syncing"]: glow_delay = 65
        elif self.status == "Downloading":
            speed_mb = (self.current_speed or 0) / (1024 * 1024)
            glow_delay = max(10, min(40, int(40 - (speed_mb * 3))))
        else:
            glow_delay = 30

        self.view.after(glow_delay, self.animate_glow)

    def download_progress_hook(self, d):
        if d['status'] == 'downloading':
            self.current_speed = d.get('speed', 0)
            percent_str = d.get('_percent_str', '0.0%').strip().replace('%', '')
            try:
                percent_str = re.sub(r'\x1b\[[0-9;]*m', '', percent_str)
                percent = float(percent_str)
            except ValueError:
                percent = 0.0
            
            bar_len = 20
            filled = int(bar_len * percent / 100)
            bar = '=' * filled + '>' + ' ' * max(0, bar_len - filled - 1)
            if filled == bar_len:
                bar = '=' * bar_len
                
            progress_line = f">> DOWNLOADING: [{bar}] {percent:.1f}%"
            if hasattr(self.view, 'after'):
                self.view.after(0, self.update_progress_ui, progress_line)
                
        elif d['status'] == 'finished':
            if hasattr(self.view, 'after'):
                self.view.after(0, self.update_progress_ui, ">> DOWNLOADING: [====================] 100.0%\n")

    def update_progress_ui(self, text):
        if not hasattr(self.view, 'get_last_log_line'):
            print(text)
            return
            
        last_line_text = self.view.get_last_log_line()
        if last_line_text.startswith(">> DOWNLOADING:"):
            self.view.replace_last_log_line(text)
        else:
            self.view.log_message(text)

    def ui_log(self, text):
        if hasattr(self.view, 'after') and hasattr(self.view, 'log_message'):
            self.view.after(0, self.view.log_message, text)
        else:
            print(text)

    def sync_event(self):
        if not hasattr(self.view, 'url_entry'):
            return
            
        url = self.view.url_entry.get().strip()
        if url:
            self.ui_log(f"\n[SYSTEM] INITIATING CRATE SYNC FOR: {url}")
            thread = threading.Thread(target=self._process_sync_thread, args=(url,))
            thread.daemon = True
            thread.start()
        else:
            self.ui_log("\n[ERROR] NO INPUT DETECTED.")

    def log_failed_sync(self, track_info, error):
        with open("failed_syncs.txt", "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {track_info} | Error: {error}\n")

    def _process_sync_thread(self, url):
        self.status = "Scanning"
        self.ui_log(">> ANALYZING SOURCE...")
        
        try:
            # Gebruik de UniversalMatcher voor intelligente detectie
            tracks_to_process = self.matcher.get_tracks(url)
            
            if tracks_to_process:
                self.ui_log(f">> PLAYLIST/ALBUM DETECTED. FOUND {len(tracks_to_process)} TRACKS.")
                for idx, track_data in enumerate(tracks_to_process, 1):
                    self.status = "Downloading"
                    self.ui_log(f"\n>> [{idx}/{len(tracks_to_process)}] SYNCING: {track_data['artist']} - {track_data['title']}")
                    
                    # Gebruik SoundCloud Search als fallback voor YouTube captcha (Tidal tracks via SC downloaden als alternatief)
                    search_query = f"scsearch:{track_data['artist']} {track_data['title']}"
                    success, result = self.core.download_track(search_query, format_choice="flac", progress_callback=self.download_progress_hook)
                    
                    if success:
                        self.status = "Syncing"
                        self.ui_log(">> EMBEDDING METADATA...")
                        self.core.update_metadata(result, artist=track_data['artist'], title=track_data['title'])
                        
                        from engine_db_handler import EngineDBHandler
                        db = EngineDBHandler(self.db_path, dry_run=True) 
                        db_success = db.add_track_to_db(result, track_data)
                        db.close()
                        
                        if db_success:
                            self.ui_log(f">> [OK] {track_data['title']} geregistreerd in Crate.")
                        else:
                            self.ui_log(f">> [ERROR] DB injectie faalde voor {track_data['title']}")
                    else:
                        self.ui_log(f">> [FAIL] Kon {track_data['title']} niet downloaden.")
                        self.log_failed_sync(f"{track_data['artist']} - {track_data['title']}", result)
            else:
                # Directe URL / Fallback if matcher yields nothing
                self.status = "Downloading"
                self.ui_log(f">> NO MATCH DATA. FALLBACK TO DIRECT SYNC: {url}")
                
                success, result = self.core.download_track(url, format_choice="flac", progress_callback=self.download_progress_hook)
                
                if success:
                    self.status = "Syncing"
                    self.ui_log(">> INJECTING UNIVERSAL LIBRARIES...")
                    
                    artist_title = os.path.basename(result).replace(".flac", "").replace(".mp3", "")
                    parts = artist_title.split(" - ", 1)
                    artist = parts[0] if len(parts) > 1 else "Unknown Artist"
                    title = parts[1] if len(parts) > 1 else artist_title
                    
                    self.core.update_metadata(result, artist=artist, title=title)
                    
                    track_data = {"artist": artist, "title": title, "bpm": 120.0, "key": ""}
                    
                    from engine_db_handler import EngineDBHandler
                    db = EngineDBHandler(self.db_path, dry_run=True) 
                    db_success = db.add_track_to_db(result, track_data)
                    db.close()

                    if db_success:
                        self.ui_log(">> [OK] Track veilig geregistreerd in m.db")
                    else:
                        self.ui_log(">> [ERROR] Database injectie gefaald.")
                else:
                    raise Exception(result)

        except Exception as e:
            self.status = "Error"
            self.ui_log(f">> [FATAL] Sync crashte: {e}")
            self.log_failed_sync(url, str(e))
        
        finally:
            self.status = "Idle"
            self.ui_log("\n[SYSTEM] CRATE SYNC OPERATION FINISHED.")

    def change_theme(self, theme_name):
        if hasattr(self.view, 'apply_theme'):
            self.view.apply_theme(theme_name)

    def open_downloads_folder(self):
        import platform
        import subprocess
        
        dl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
        if not os.path.exists(dl_path):
            os.makedirs(dl_path)
            
        if platform.system() == "Windows":
            os.startfile(dl_path)
        elif platform.system() == "Darwin":
            subprocess.call(["open", dl_path])
        else:
            subprocess.call(["xdg-open", dl_path])

    def scan_health_event(self):
        print("Scan health stub")

    def settings_event(self):
        if hasattr(self.view, 'settings_event'):
            self.view.settings_event()
        else:
            self.ui_log(">> [GUI] Settings menu opened.")
