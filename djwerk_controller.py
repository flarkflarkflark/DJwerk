import os
import threading
import time
import re
from datetime import datetime
from typing import Optional
from models.config import THEMES
from djwerk_core import DJwerkCore
from djwerk_matcher import UniversalMatcher
from universal_db import UniversalDBHandler
from rekordbox_xml import RekordboxXMLGenerator
from crate_health import CrateHealthScanner
from engine_integrity import DatabaseValidator

class DJwerkController:
    """The Controller in DJwerk's MVC pattern."""

    def __init__(self, view):
        self.view = view
        self.core = DJwerkCore()
        self.db_path = "m.db"
        
        self.universal_db = UniversalDBHandler(self.db_path)
        self.rb_xml = RekordboxXMLGenerator("library.xml")
        self.health_scanner = CrateHealthScanner()

        # PERSISTENT API HANDLERS
        from tidal_api_handler import TidalApiHandler
        from spotify_api_handler import SpotifyApiHandler
        from bandcamp_api_handler import BandcampApiHandler
        self.tidal_api = TidalApiHandler()
        self.spotify_api = SpotifyApiHandler()
        self.bc_api = BandcampApiHandler()
        
        self.matcher = UniversalMatcher(spotify_api=self.spotify_api, tidal_api=self.tidal_api, bandcamp_api=self.bc_api)

        self.status = "Idle"
        self.energy_level = 0.5
        self.last_playlist_path = getattr(self.view, "last_playlist_path", None)
        self.last_synced_tracks = []
        self.cancel_event = threading.Event()

        self.view.sync_btn.configure(command=self.sync_event)
        
        if hasattr(self.view, 'downloads_btn'):
            self.view.downloads_btn.configure(command=self.open_downloads_folder)
            
        if hasattr(self.view, 'settings_btn'):
            self.view.settings_btn.configure(command=self.settings_event)
        
        if hasattr(self.view, 'bind'):
            self.view.bind("<<SettingsUpdated>>", lambda e: self._handle_settings_update())
            self.view.bind("<<YoloSyncEvent>>", lambda e: self.yolo_sync_event())
            self.view.bind("<<ConnectTidalEvent>>", lambda e: self.connect_tidal())
            self.view.bind("<<ConnectSpotifyEvent>>", lambda e: self.connect_spotify())
            self.view.bind("<<ConnectBandcampEvent>>", lambda e: self.connect_bandcamp())
            self.view.bind("<<OpenLastFolderEvent>>", lambda e: self.open_last_playlist_folder())
            self.view.bind("<<RefreshStatusesEvent>>", lambda e: threading.Thread(target=self._refresh_connection_statuses, daemon=True).start())
            self.view.bind("<<CancelSyncEvent>>", lambda e: self.cancel_sync())
            self.view.bind("<<ExportRekordboxEvent>>", lambda e: self.export_rekordbox())
            self.view.bind("<<ExportEngineEvent>>", lambda e: self.export_engine())
            self.view.bind("<<ExportMixxxEvent>>", lambda e: self.export_mixxx())
            self.view.bind("<<ExportM3UEvent>>", lambda e: self.export_m3u_rich())
        
        if hasattr(self.view, 'log_message'):
            self.initialize_ui_log()
            
        self._refresh_connection_statuses()

    def cancel_sync(self):
        if self.status != "Idle":
            self.ui_log("\n>> [SYSTEM] CANCELLATION REQUESTED. CLEANING UP...")
            self.cancel_event.set()

    def initialize_ui_log(self):
        self.view.log_message(">> DJwerk PRO COMMAND CENTER: V0.1.0")
        self.view.log_message(">> System: LINUX BRIDGE ACTIVE")
        self.view.log_message(">> Universal XML: library.xml LOADED")
        self.view.log_message(">> Awaiting URL Input...")

    def _handle_settings_update(self):
        creds = getattr(self.view, 'credentials', {})
        if hasattr(self, 'spotify_api'):
            self.spotify_api.update_credentials(creds.get("spotify_client_id"), creds.get("spotify_client_secret"))
        if hasattr(self, 'bc_api') and creds.get("bandcamp_username"):
            self.bc_api.login(creds.get("bandcamp_username"))
        self._refresh_connection_statuses()

    def _refresh_connection_statuses(self):
        # Fetch statuses
        self.view.tidal_logged_in = self.tidal_api.check_login()
        
        # UNIVERSAL BROWSER CHECK: We checken of de browser cookies heeft voor de services
        browser = getattr(self.view, "cookies_browser", "none")
        
        # We halen alle cookies in één keer op voor maximale snelheid
        browser_cookies = []
        if browser != "none":
            try:
                import yt_dlp
                ydl_opts = {'quiet': True, 'no_warnings': True, 'cookiesfrombrowser': (browser,)}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    browser_cookies = [c for c in ydl.cookiejar]
            except:
                pass

        def has_auth(domain):
            return any(domain in c.domain for c in browser_cookies)

        # Spotify status (OAuth of Browser)
        spotify_oauth = self.spotify_api.check_login() if hasattr(self.spotify_api, "check_login") else False
        self.view.spotify_logged_in = spotify_oauth or has_auth("spotify")
        
        # Bandcamp status
        self.view.bandcamp_logged_in = self.bc_api.logged_in or has_auth("bandcamp")
        
        # SoundCloud status
        sc_connected = has_auth("soundcloud")
        
        # Update UI labels
        if hasattr(self.view, "service_status_labels"):
            labels = self.view.service_status_labels
            
            def update_lbl(name, connected):
                if name in labels:
                    txt = "CONNECTED" if connected else "DISCONNECTED"
                    clr = "#44FF44" if connected else "#FF4444"
                    if hasattr(self.view, "after"):
                        self.view.after(0, lambda l=labels[name], t=txt, c=clr: l.configure(text=t, text_color=c))
                    else:
                        labels[name].configure(text=txt, text_color=clr)

            update_lbl("tidal", self.view.tidal_logged_in or has_auth("tidal"))
            update_lbl("spotify", self.view.spotify_logged_in)
            update_lbl("bandcamp", self.view.bandcamp_logged_in)
            update_lbl("soundcloud", sc_connected)

    def connect_tidal(self):
        def on_login_details(link, code):
            import webbrowser
            webbrowser.open(link, new=2)
            if hasattr(self.view, "after"):
                self.view.after(0, self.view.show_tidal_login, link, code, None)
        thread = threading.Thread(target=self.tidal_api.start_login_flow, args=(on_login_details,))
        thread.daemon = True
        thread.start()

    def connect_spotify(self):
        auth_url = self.spotify_api.get_auth_url()
        import webbrowser
        webbrowser.open(auth_url)

    def connect_bandcamp(self):
        import customtkinter as ctk
        dialog = ctk.CTkInputDialog(text="Enter Bandcamp Username:", title="Connect Bandcamp")
        username = dialog.get_input()
        if username and self.bc_api.login(username):
            self.view.bandcamp_logged_in = True

    def open_last_playlist_folder(self):
        if not self.last_playlist_path or not os.path.exists(self.last_playlist_path):
            self.ui_log(">> [INFO] NO RECENT PLAYLIST SYNCED YET.")
            return
        
        import platform, subprocess
        try:
            if platform.system() == "Windows":
                os.startfile(self.last_playlist_path)
            elif platform.system() == "Darwin":
                subprocess.call(["open", self.last_playlist_path])
            else:
                subprocess.call(["xdg-open", self.last_playlist_path])
        except Exception as e:
            self.ui_log(f">> [ERROR] COULD NOT OPEN FOLDER: {e}")

    def export_rekordbox(self):
        self.ui_log("\n>> [EXPORT] UPDATING REKORDBOX XML...")
        try:
            self.rb_xml.save()
            self.ui_log(">> [SUCCESS] library.xml UPDATED. IMPORT IN REKORDBOX VIA 'XML' SIDEBAR.")
        except Exception as e:
            self.ui_log(f">> [ERROR] REKORDBOX EXPORT FAILED: {e}")

    def export_engine(self):
        if not self.last_synced_tracks:
            self.ui_log("\n>> [WARN] NO RECENT TRACKS TO EXPORT TO ENGINE DJ.")
            return
        
        self.ui_log(f"\n>> [EXPORT] PUSHING {len(self.last_synced_tracks)} TRACKS TO ENGINE DJ...")
        count = 0
        for track in self.last_synced_tracks:
            if self.universal_db.inject_engine_dj(track['path'], track):
                count += 1
        self.ui_log(f">> [SUCCESS] {count} TRACKS INJECTED INTO m.db.")

    def export_mixxx(self):
        if not self.last_synced_tracks:
            self.ui_log("\n>> [WARN] NO RECENT TRACKS TO EXPORT TO MIXXX.")
            return
            
        import platform
        # Standard location check
        if platform.system() == "Linux":
            mixxx_db = os.path.expanduser("~/.mixxx/mixxxdb.sqlite")
            if not os.path.exists(mixxx_db):
                # Try Flatpak
                mixxx_db = os.path.expanduser("~/.var/app/org.mixxx.Mixxx/config/mixxx/mixxxdb.sqlite")
        elif platform.system() == "Darwin": # macOS
            mixxx_db = os.path.expanduser("~/Library/Application Support/Mixxx/mixxxdb.sqlite")
        elif platform.system() == "Windows":
            mixxx_db = os.path.join(os.environ.get('LOCALAPPDATA', ''), "Mixxx", "mixxxdb.sqlite")
        else:
            mixxx_db = ""
            
        if not mixxx_db or not os.path.exists(mixxx_db):
            self.ui_log(">> [ERROR] MIXXX DATABASE NOT FOUND AT DEFAULT LOCATIONS.")
            return

        self.ui_log(f"\n>> [EXPORT] PUSHING {len(self.last_synced_tracks)} TRACKS TO MIXXX...")
        count = 0
        for track in self.last_synced_tracks:
            if self.universal_db.inject_mixxx(mixxx_db, track['path'], track):
                count += 1
        self.ui_log(f">> [SUCCESS] {count} TRACKS INJECTED INTO MIXXX.")

    def export_m3u_rich(self):
        if not self.last_playlist_path or not self.last_synced_tracks:
            self.ui_log("\n>> [WARN] NO RECENT PLAYLIST TO ENRICH.")
            return
            
        self.ui_log("\n>> [EXPORT] GENERATING RICH M3U8 FOR DJAY / SERATO...")
        playlist_name = os.path.basename(self.last_playlist_path)
        rich_m3u_path = os.path.join(self.last_playlist_path, f"{playlist_name}_RICH.m3u8")
        
        try:
            with open(rich_m3u_path, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for t in self.last_synced_tracks:
                    # Extended M3U info: #EXTINF:duration,artist - title
                    duration = int(t.get('duration', 0))
                    f.write(f"#EXTINF:{duration},{t['artist']} - {t['title']}\n")
                    f.write(f"{os.path.basename(t['path'])}\n")
            self.ui_log(f">> [SUCCESS] RICH PLAYLIST GENERATED: {os.path.basename(rich_m3u_path)}")
        except Exception as e:
            self.ui_log(f">> [ERROR] RICH M3U EXPORT FAILED: {e}")

    def ui_log(self, text):
        try:
            if hasattr(self.view, 'after') and hasattr(self.view, 'log_message'):
                if self.view.winfo_exists(): self.view.after(0, self.view.log_message, text)
                else: print(text)
            else: print(text)
        except: print(text)

    def sync_event(self):
        url = self.view.url_entry.get().strip()
        if url:
            self.cancel_event.clear()
            self.ui_log(f"\n[SYSTEM] INITIATING CRATE SYNC FOR: {url}")
            thread = threading.Thread(target=self._process_sync_thread, args=(url,))
            thread.daemon = True
            thread.start()
        else: self.ui_log("\n[ERROR] NO INPUT DETECTED.")

    def yolo_sync_event(self):
        try:
            raw_text = self.view.clipboard_get()
            if raw_text and len(raw_text) > 10:
                self.cancel_event.clear()
                self.ui_log(f"\n[SYSTEM] INITIATING CLIPBOARD SYNC...")
                thread = threading.Thread(target=self._process_sync_thread, args=(raw_text,))
                thread.daemon = True
                thread.start()
            else:
                self.ui_log("\n[INFO] CLIPBOARD TEXT TOO SHORT. PLEASE COPY MORE TRACK DATA.")
        except Exception:
            self.ui_log("\n[INFO] CLIPBOARD IS EMPTY. PLEASE COPY SOME TEXT FIRST.")

    def _process_sync_thread(self, url):
        self.status = "Scanning"
        self.ui_log(">> ANALYZING SOURCE...")
        
        if self.cancel_event.is_set(): return

        if "tidal.com" in url and not self.tidal_api.check_login():
            def on_login_details(link, code):
                import webbrowser
                webbrowser.open(link, new=2)
                if hasattr(self.view, "after"): self.view.after(0, self.view.show_tidal_login, link, code, None)
            if not self.tidal_api.start_login_flow(on_login_details):
                self.status = "Idle"; return

        cookies_browser = getattr(self.view, "cookies_browser", "none")
        try:
            tracks_to_process = self.matcher.get_tracks(url, cookies_from_browser=cookies_browser)
            
            if self.cancel_event.is_set(): return

            if tracks_to_process:
                self.ui_log(f">> DETECTED {len(tracks_to_process)} TRACKS.")
                if hasattr(self.view, "after"): self.view.after(0, self.view.show_track_selector, tracks_to_process, self.start_selected_sync)
                else: self.start_selected_sync(tracks_to_process)
            else:
                self.ui_log(">> [ERROR] NO VALID TRACK DATA DETECTED.")
                self.ui_log("\n>> WHAT CAN YOU PASTE HERE?")
                self.ui_log("   1. URLs from Tidal, Spotify, SoundCloud or Bandcamp.")
                self.ui_log("   2. A block of text with tracks in 'Artist - Title' format.")
                self.ui_log("   3. A list of tracks from your browser (select & copy).")
                self.ui_log("\n>> TIP: Make sure your text lines contain a ' - ' or ' : ' separator.")
        except Exception as e: self.ui_log(f">> [FATAL] Crash: {e}")
        finally:
            if not tracks_to_process: self.status = "Idle"

    def start_selected_sync(self, selected_tracks, chosen_format="FLAC (Lossless)", crate_name="Synced Crate"):
        if not selected_tracks: self.status = "Idle"; return
        self.cancel_event.clear()
        self.ui_log(f"\n[SYSTEM] STARTING SYNC FOR {len(selected_tracks)} TRACKS...")
        thread = threading.Thread(target=self._run_download_batch, args=(selected_tracks, chosen_format, crate_name))
        thread.daemon = True
        thread.start()

    def _run_download_batch(self, tracks, chosen_format, crate_name="Synced Crate"):
        self.status = "Downloading"
        self.last_synced_tracks = []
        cookies_browser = getattr(self.view, "cookies_browser", "none")
        preferred_format = "flac" if "FLAC" in chosen_format else "mp3"
        synced_filenames = []

        # We halen de source uit de eerste track voor de hoofdmap
        main_source = tracks[0].get('source', 'Unknown')
        
        # Basis pad: downloads/[Source]/[Crate] [FORMAT]/
        fmt_tag = f"[{preferred_format.upper()}]"
        playlist_folder = f"{crate_name.replace('/', '_').replace('\\', '_')} {fmt_tag}"
        source_folder = os.path.join(self.core.download_path, main_source.capitalize())
        self.last_playlist_path = os.path.join(source_folder, playlist_folder)
        
        # PERSIST LAST SYNCED PLAYLIST
        if hasattr(self.view, "save_config"):
            self.view.last_playlist_path = self.last_playlist_path
            self.view.save_config()
        
        # DOWNLOAD PLAYLIST COVER (folder.jpg)
        playlist_cover_url = tracks[0].get('playlist_cover')
        local_cover_path = None
        if playlist_cover_url:
            self.ui_log(f"\n[SYSTEM] DOWNLOADING CRATE ARTWORK...")
            local_cover_path = self.core.download_image(playlist_cover_url, self.last_playlist_path)
            if local_cover_path:
                self.ui_log(f">> SAVED: {os.path.basename(local_cover_path)}")

        try:
            for idx, track_data in enumerate(tracks, 1):
                if self.cancel_event.is_set():
                    self.ui_log("\n>> [SYSTEM] SYNC HALTED BY USER.")
                    break

                # SMART QUALITY LOGIC
                target_format = preferred_format
                if preferred_format == "flac" and not track_data.get('is_lossless', False):
                    target_format = "mp3"
                    self.ui_log(f"\n> [SMART SYNC] {track_data['title']}: SOURCE IS LOSSY. FORCING MP3.")

                self.ui_log(f"\n> SYNCING [{idx:03d}/{len(tracks):03d}]: {track_data['artist']} - {track_data['title']} ({target_format.upper()})")
                if 'bpm' in track_data and track_data['bpm']:
                    self.ui_log(f"> METADATA: {track_data['bpm']} BPM | Key: {track_data.get('key', 'N/A')}")

                # Check met de nieuwe bron-specifieke folder
                if self.core.is_track_downloaded(track_data['artist'], track_data['title'], target_format, os.path.join(main_source.capitalize(), playlist_folder)):
                    self.ui_log("> SKIPPING: Already exists.")
                    continue

                if idx > 1: time.sleep(2.0)
                
                if self.cancel_event.is_set(): break

                url = track_data.get('url') or f"scsearch:{track_data['artist']} {track_data['title']}"
                success, result, s_info = self.core.download_track(
                    url, target_format, self.download_progress_hook, 
                    cookies_browser, playlist_folder, idx, 
                    artist=track_data['artist'], source=main_source
                )
                
                if success:
                    abr = s_info.get('abr', 0)
                    self.ui_log(f"> SOURCE: {s_info.get('acodec', '??').upper()} @ {abr} kbps")
                    
                    if self.cancel_event.is_set(): break

                    # SMART NORMALIZATION (Optioneel)
                    gain_enabled = getattr(self.view, "pref_gain_enabled", False)
                    if gain_enabled:
                        target = getattr(self.view, "pref_gain_target", "-14 LUFS (Standard)")
                        self.ui_log(f"> NORMALIZING: Target {target}...")
                        if self.core.normalize_audio(result, target):
                            self.ui_log("> [SUCCESS] Audio Leveled.")
                        else: self.ui_log("> [WARN] Normalization failed.")

                    self.core.update_metadata(
                        result, track_data['artist'], track_data['title'], 
                        track_data.get('album'), track_data.get('bpm'), 
                        track_data.get('key'), cover_path=local_cover_path, index=idx
                    )
                    self.rb_xml.add_track(result, track_data['artist'], track_data['title'], track_data.get('album'), track_data.get('bpm', 120.0), track_data.get('key', ''))
                    self.rb_xml.save()
                    
                    # Store for selective export
                    self.last_synced_tracks.append({
                        'path': result,
                        'artist': track_data['artist'],
                        'title': track_data['title'],
                        'album': track_data.get('album', ''),
                        'bpm': track_data.get('bpm', 120.0),
                        'key': track_data.get('key', ''),
                        'duration': track_data.get('duration', 0)
                    })
                    
                    self.ui_log(f"> [SUCCESS] Saved.")
                    
                    # Track toevoegen aan de M3U lijst (alleen de bestandsnaam voor relatieve paden)
                    synced_filenames.append(os.path.basename(result))
                else: self.ui_log(f"> [FAILED] {result}")
            
            if self.cancel_event.is_set(): return

            # PLAYLIST GENERATIE (.m3u8)
            if synced_filenames:
                playlist_name = playlist_folder if playlist_folder else f"Sync_{datetime.now().strftime('%Y%m%d_%H%M')}"
                # BELANGRIJK: De playlist file staat in de root van de playlist map
                playlist_path = os.path.join(self.last_playlist_path, f"{playlist_name}.m3u8")
                
                with open(playlist_path, "w", encoding="utf-8") as f:
                    f.write("#EXTM3U\n")
                    for fname in synced_filenames:
                        f.write(f"{fname}\n")
                
                self.ui_log(f"\n[PLAYLIST] GENERATED: {os.path.basename(playlist_path)}")
                self.ui_log(f">> Location: {playlist_path}")

        except Exception as e: self.ui_log(f">> [FATAL] Batch sync crashte: {e}")
        finally: self.status = "Idle"; self.ui_log("\n[SYSTEM] FINISHED.")

    def download_progress_hook(self, d):
        if d['status'] == 'downloading':
            percent = float(re.sub(r'\x1b\[[0-9;]*m', '', d.get('_percent_str', '0.0%').strip().replace('%', '')))
            bar = '=' * int(20 * percent / 100) + '>' + ' ' * (20 - int(20 * percent / 100) - 1)
            self.view.after(0, self.update_progress_ui, f">> DOWNLOADING: [{bar[:20]}] {percent:.1f}%")
        elif d['status'] == 'finished':
            self.view.after(0, self.update_progress_ui, ">> DOWNLOADING: [====================] 100.0%\n")

    def update_progress_ui(self, text):
        if not hasattr(self.view, 'get_last_log_line'): return
        if self.view.get_last_log_line().startswith(">> DOWNLOADING:"): self.view.replace_last_log_line(text)
        else: self.view.log_message(text)

    def settings_event(self):
        if hasattr(self.view, 'settings_event'): self.view.settings_event()

    def open_downloads_folder(self):
        import platform, subprocess
        dl_path = self.core.download_path
        cmd = "xdg-open" if platform.system() == "Linux" else "open" if platform.system() == "Darwin" else "start"
        subprocess.call([cmd, dl_path])
