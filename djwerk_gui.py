import customtkinter as ctk
import tkinter as tk
from PIL import Image
import os
import platform
import subprocess
import json

ORANGE = "#FF8C00"
DARK_GREY = "#1a1a1a"
MID_GREY = "#2b2b2b"
GLOW_BLACK = "#0a0a0a"
CONFIG_FILE = ".djwerk_config.json"

class CTKToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        if self.tooltip_window or not self.text: return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)
        
        label = tk.Label(tw, text=self.text, justify='left',
                       background="#FF8C00", foreground="black", 
                       relief='solid', borderwidth=1,
                       font=("Helvetica", "10", "normal"), padx=5, pady=2)
        label.pack(ipadx=1)

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

class InteractiveValue(ctk.CTkLabel):
    """A label that can be scrolled or clicked to change numeric values."""
    def __init__(self, master, variable, unit="LUFS", min_val=-24.0, max_val=0.0, step=0.5, **kwargs):
        super().__init__(master, textvariable=variable, cursor="hand2", **kwargs)
        self.variable = variable
        self.unit = unit
        self.min_val = min_val
        self.max_val = max_val
        self.step = step
        
        self.bind("<Enter>", lambda e: self.configure(text_color=ORANGE))
        self.bind("<Leave>", lambda e: self.configure(text_color="#ffffff"))
        
        # Scroll bindings
        self.bind("<Button-4>", self._scroll_up)
        self.bind("<Button-5>", self._scroll_down)
        self.bind("<MouseWheel>", self._scroll_win)
        
        # Click to edit
        self.bind("<Button-1>", self._on_click)

    def _get_val(self):
        try:
            raw = self.variable.get().split(" ")[0]
            return float(raw)
        except: return -14.0

    def _set_val(self, val):
        val = max(self.min_val, min(self.max_val, val))
        if self.unit == "dB":
            self.variable.set(f"{val:+.1f} dB")
        else:
            self.variable.set(f"{val:.1f} LUFS")

    def _scroll_up(self, e): self._set_val(self._get_val() + self.step)
    def _scroll_down(self, e): self._set_val(self._get_val() - self.step)
    def _scroll_win(self, e):
        if e.delta > 0: self._set_val(self._get_val() + self.step)
        else: self._set_val(self._get_val() - self.step)

    def _on_click(self, e):
        # Click popup removed as requested
        pass

class ExportCenterWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("DJwerk - Export Center")
        self.geometry("600x500")
        self.configure(fg_color=DARK_GREY)
        self.attributes("-topmost", True)
        
        ctk.CTkLabel(self, text="🚀 EXPORT CENTER", font=ctk.CTkFont(size=24, weight="bold"), text_color="#3498db").pack(pady=(20, 10))
        ctk.CTkLabel(self, text="Select your target DJ software to push your crates.", font=ctk.CTkFont(size=13), text_color="#777").pack(pady=(0, 20))

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=30, pady=10)

        def draw_export_option(name, description, color, event_name):
            row = ctk.CTkFrame(container, fg_color=MID_GREY, corner_radius=10, height=80)
            row.pack(fill="x", pady=5)
            
            info_frame = ctk.CTkFrame(row, fg_color="transparent")
            info_frame.pack(side="left", padx=20, fill="y")
            
            ctk.CTkLabel(info_frame, text=name, font=ctk.CTkFont(size=16, weight="bold"), text_color=color, anchor="w").pack(pady=(10, 0))
            ctk.CTkLabel(info_frame, text=description, font=ctk.CTkFont(size=11), text_color="#aaa", anchor="w").pack()
            
            btn = ctk.CTkButton(row, text="PUSH", width=80, fg_color=color, text_color="black", font=ctk.CTkFont(weight="bold"), 
                               command=lambda: parent.event_generate(event_name))
            btn.pack(side="right", padx=20, pady=20)

        draw_export_option("Rekordbox", "Generate / Update library.xml for Pioneer DJ", ORANGE, "<<ExportRekordboxEvent>>")
        draw_export_option("Engine DJ", "Direct database injection into m.db (Denon/Numark)", "#00ff00", "<<ExportEngineEvent>>")
        draw_export_option("Mixxx", "Inject tracks into mixxxdb.sqlite (Linux/Mac/Win)", "#e67e22", "<<ExportMixxxEvent>>")
        draw_export_option("djay Pro / Serato", "Export Extended M3U8 with rich metadata", "#3498db", "<<ExportM3UEvent>>")

        ctk.CTkButton(self, text="CLOSE", fg_color="#444", command=self.destroy).pack(pady=20)

class TrackSelectorWindow(ctk.CTkToplevel):
    def __init__(self, parent, tracks, on_confirm):
        super().__init__(parent)
        self.title("DJwerk - Crate Selector")
        self.geometry("850x650")
        self.configure(fg_color=DARK_GREY)
        self.attributes("-topmost", True)
        
        self.all_tracks = tracks
        self.on_confirm = on_confirm
        self.checkboxes = []
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Header & Filter
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        
        ctk.CTkLabel(header_frame, text=f"Detected {len(tracks)} tracks. Select to Sync:", font=ctk.CTkFont(size=16, weight="bold"), text_color=ORANGE).pack(side="left")
        
        self.search_entry = ctk.CTkEntry(header_frame, placeholder_text="Filter by Artist or Title...", width=300, border_color=ORANGE)
        self.search_entry.pack(side="right", padx=10)
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh_list())

        # Bulk Actions & Format Selection
        bottom_frame = ctk.CTkFrame(self, fg_color=MID_GREY, corner_radius=0)
        bottom_frame.grid(row=3, column=0, sticky="ew")
        
        # NIEUW: Crate Name aanpasbaar maken
        crate_settings_frame = ctk.CTkFrame(self, fg_color="transparent")
        crate_settings_frame.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        source_name = tracks[0].get('source', 'Unknown').upper() if tracks else 'UNKNOWN'
        ctk.CTkLabel(crate_settings_frame, text=f"DESTINATION CRATE IN [{source_name}]:", font=ctk.CTkFont(weight="bold"), text_color=ORANGE).pack(side="left")
        
        default_crate_name = "Synced Crate"
        if tracks and tracks[0].get('is_playlist'):
            default_crate_name = tracks[0].get('album', 'Synced Crate')
        
        self.crate_entry = ctk.CTkEntry(crate_settings_frame, width=400, border_color=ORANGE, fg_color=GLOW_BLACK)
        self.crate_entry.pack(side="left", padx=10)
        self.crate_entry.insert(0, default_crate_name)

        bulk_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        bulk_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkButton(bulk_frame, text="Select All", width=100, fg_color=DARK_GREY, command=self.select_all).pack(side="left", padx=5)
        ctk.CTkButton(bulk_frame, text="Select None", width=100, fg_color=DARK_GREY, command=self.select_none).pack(side="left", padx=5)
        
        # CHIQUE: Formaat keuze hier in de balk
        ctk.CTkLabel(bulk_frame, text="FORMAT:", font=ctk.CTkFont(weight="bold"), text_color=ORANGE).pack(side="left", padx=(30, 5))
        
        # AUTO-SELECT FORMAT & OPTIONS
        any_lossless = any(t.get('is_lossless', False) for t in tracks)
        format_options = ["FLAC (Lossless)", "MP3 (320 kbps)"] if any_lossless else ["MP3 (320 kbps)"]
        default_format = "FLAC (Lossless)" if any_lossless else "MP3 (320 kbps)"
        
        self.format_var = ctk.StringVar(value=default_format)
        self.format_menu = ctk.CTkOptionMenu(bulk_frame, values=format_options, variable=self.format_var, fg_color=GLOW_BLACK, button_color=ORANGE, width=150)
        self.format_menu.pack(side="left", padx=5)

        self.sync_btn = ctk.CTkButton(bulk_frame, text="START SYNC SELECTED", fg_color=ORANGE, text_color="black", font=ctk.CTkFont(weight="bold"), command=self.confirm)
        self.sync_btn.pack(side="right", padx=5)

        # Scrollable List
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color=GLOW_BLACK, border_width=1, border_color="#333")
        self.scroll_frame.grid(row=1, column=0, padx=20, pady=0, sticky="nsew")
        
        self.refresh_list()

    def refresh_list(self):
        # Clear existing
        for cb in self.checkboxes:
            cb.destroy()
        self.checkboxes = []
        
        query = self.search_entry.get().lower()
        
        def _format_duration(seconds):
            if not seconds: return "??:??"
            m, s = divmod(int(seconds), 60)
            return f"{m:02d}:{s:02d}"

        for i, track in enumerate(self.all_tracks):
            # SOURCE & QUALITY TAGS (Pro-Grade display)
            src = track.get('source', 'SEARCH').upper()
            qual = "FLAC" if track.get('is_lossless') else "MP3"
            dur = _format_duration(track.get('duration'))
            
            display_text = f"[{src} | {qual}] [{dur}] {track['artist']} - {track['title']}"
            if query and query not in display_text.lower():
                continue
                
            cb = ctk.CTkCheckBox(self.scroll_frame, text=display_text, text_color="#ffffff", border_color=ORANGE, hover_color=ORANGE)
            cb.pack(fill="x", padx=10, pady=5)
            cb.select() # Default aan
            # We store the original track object in the widget for easy retrieval
            cb.track_data = track
            self.checkboxes.append(cb)

    def select_all(self):
        for cb in self.checkboxes:
            cb.select()
            
    def select_none(self):
        for cb in self.checkboxes:
            cb.deselect()

    def confirm(self):
        selected = [cb.track_data for cb in self.checkboxes if cb.get()]
        chosen_format = self.format_var.get()
        crate_name = self.crate_entry.get().strip() or "Synced Crate"
        self.on_confirm(selected, chosen_format, crate_name)
        self.destroy()

class DJwerkApp(ctk.CTk):
    def __init__(self, core_engine):
        super().__init__()
        self.core = core_engine
        self.title("DJwerk v0.1.0 - Universal Crate Engine [flarkAUDIO]")
        self.geometry("1000x700")
        self.configure(fg_color=DARK_GREY)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Load settings
        self.load_config()

        # Zijbalk
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=MID_GREY)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.logo_label = ctk.CTkLabel(self.sidebar, text="DJwerk", font=ctk.CTkFont(size=28, weight="bold"), text_color=ORANGE)
        self.logo_label.pack(pady=30)

        self.sync_btn = ctk.CTkButton(self.sidebar, text="Sync Crate", fg_color=ORANGE, text_color="black", font=ctk.CTkFont(weight="bold"), command=lambda: self.event_generate("<<SyncEvent>>"))
        self.sync_btn.pack(padx=20, pady=10, fill="x")
        CTKToolTip(self.sync_btn, "Analyzes the URL and starts the Crate Selector")

        self.cancel_btn = ctk.CTkButton(self.sidebar, text="CANCEL SYNC", fg_color="#444", text_color="#aaa", font=ctk.CTkFont(weight="bold"), command=lambda: self.event_generate("<<CancelSyncEvent>>"))
        self.cancel_btn.pack(padx=20, pady=(0, 10), fill="x")
        CTKToolTip(self.cancel_btn, "Halt all active synchronization processes (ESC)")

        self.export_btn = ctk.CTkButton(self.sidebar, text="EXPORT CENTER", fg_color="transparent", border_width=1, border_color="#3498db", text_color="#3498db", font=ctk.CTkFont(weight="bold"), command=self.export_center_event)
        self.export_btn.pack(padx=20, pady=10, fill="x")
        CTKToolTip(self.export_btn, "Push your collection to Rekordbox, Engine DJ, Mixxx or djay")

        self.downloads_btn = ctk.CTkButton(self.sidebar, text="Open Downloads", fg_color="transparent", border_width=1, border_color=ORANGE, command=self.open_downloads)
        self.downloads_btn.pack(padx=20, pady=10, fill="x")
        CTKToolTip(self.downloads_btn, "Open your local DJ library folder")

        self.help_btn = ctk.CTkButton(self.sidebar, text="Help & Manual", fg_color="transparent", command=self.help_event)
        self.help_btn.pack(side="bottom", pady=(5, 20))
        CTKToolTip(self.help_btn, "Show usage instructions and platform tips")

        self.settings_btn = ctk.CTkButton(self.sidebar, text="Settings", fg_color=MID_GREY, command=self.settings_event)
        self.settings_btn.pack(side="bottom", pady=5)
        CTKToolTip(self.settings_btn, "Configure Quality, Normalization and API Keys")
        
        # Global bindings
        self.bind("<Escape>", lambda e: self.event_generate("<<CancelSyncEvent>>"))

        # Main Panel
        self.main_panel = ctk.CTkFrame(self, fg_color=DARK_GREY)
        self.main_panel.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_panel.grid_columnconfigure(0, weight=1)
        self.main_panel.grid_rowconfigure(3, weight=1) # Terminal takes all space

        # URL Input & Primary Action
        self.url_frame = ctk.CTkFrame(self.main_panel, fg_color="transparent")
        self.url_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 5))
        self.url_frame.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(self.url_frame, placeholder_text="Paste Tidal / Spotify / SoundCloud / Bandcamp / Beatport URL here...", height=45, border_color=ORANGE, fg_color=GLOW_BLACK, text_color="#ffffff", font=ctk.CTkFont(size=14))
        self.url_entry.grid(row=0, column=0, sticky="ew")
        CTKToolTip(self.url_entry, "Paste a playlist, album or track URL here")

        def clear_url():
            self.url_entry.delete(0, 'end')

        self.clear_btn = ctk.CTkButton(self.url_frame, text="X", width=30, height=30, fg_color="#333", hover_color="#555", text_color="#aaa", font=ctk.CTkFont(size=12, weight="bold"), command=clear_url)
        self.clear_btn.grid(row=0, column=0, sticky="e", padx=10)
        CTKToolTip(self.clear_btn, "Clear input field")

        self.yolo_btn = ctk.CTkButton(self.main_panel, text="PASTE & SYNC CRATE", fg_color="#8B0000", hover_color="#FF0000", text_color="white", height=40, font=ctk.CTkFont(size=15, weight="bold"), command=lambda: self.event_generate("<<YoloSyncEvent>>"))
        self.yolo_btn.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 15))
        CTKToolTip(self.yolo_btn, "Sync directly from your clipboard text block")

        # Action Bar (Folders only now)
        self.action_bar = ctk.CTkFrame(self.main_panel, fg_color="transparent")
        self.action_bar.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 10))
        
        self.close_app_btn = ctk.CTkButton(self.action_bar, text="CLOSE APP", fg_color="#444", text_color="#aaa", command=self.quit)
        self.close_app_btn.pack(side="left")

        # History Dropdown
        history_values = [os.path.basename(p) for p in self.playlist_history] if self.playlist_history else []
        if history_values:
            history_values.append("---")
            history_values.append("Clear History")
        else:
            history_values = ["No History"]
            
        self.history_var = ctk.StringVar(value="RECENT PLAYLISTS")
        
        def on_history_select(choice):
            if choice in ["No History", "---"]: 
                self.history_var.set("RECENT PLAYLISTS")
                return
            
            if choice == "Clear History":
                self.playlist_history = []
                self.save_config()
                self.history_menu.configure(values=["No History"])
                self.history_var.set("RECENT PLAYLISTS")
                return

            # Find the path matching the basename
            for path in self.playlist_history:
                if os.path.basename(path) == choice:
                    self.selected_history_path = path
                    self.event_generate("<<OpenHistoryFolderEvent>>")
                    break
            self.history_var.set("RECENT PLAYLISTS")

        self.history_menu = ctk.CTkOptionMenu(self.action_bar, values=history_values, variable=self.history_var, 
                                             command=on_history_select, fg_color="transparent", 
                                             button_color=ORANGE, button_hover_color="#cc7000",
                                             text_color=ORANGE, dynamic_resizing=False, width=250)
        self.history_menu.pack(side="right")
        CTKToolTip(self.history_menu, "Select a recent playlist to open its folder")

        # [[ PRO COMMAND CENTER ]]
        self.terminal_frame = ctk.CTkFrame(self.main_panel, fg_color=GLOW_BLACK, border_width=2, border_color="#333")
        self.terminal_frame.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.terminal_frame.grid_columnconfigure(0, weight=1)
        self.terminal_frame.grid_rowconfigure(1, weight=1)

        self.crate_log = ctk.CTkTextbox(self.terminal_frame, fg_color="transparent", text_color="#00FF00", font=ctk.CTkFont(family="Consolas", size=13))
        self.crate_log.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        # Configure color tags for the terminal
        self.crate_log.tag_config("ERROR", foreground="#FF4444")
        self.crate_log.tag_config("SUCCESS", foreground="#44FF44")
        self.crate_log.tag_config("INFO", foreground="#4444FF")
        self.crate_log.tag_config("SYSTEM", foreground=ORANGE)
        
        # Context menu
        self._create_context_menu(self.url_entry)
        
        self.log_message = self._log_message
        self.get_last_log_line = self._get_last_log_line
        self.replace_last_log_line = self._replace_last_log_line

    def show_track_selector(self, tracks, on_confirm):
        """Launches the Toplevel selector window."""
        self.selector = TrackSelectorWindow(self, tracks, on_confirm)
        self.selector.focus()
        return self.selector

    def show_tidal_login(self, link, code, on_complete):
        """Launches a device login window for Tidal."""
        login_window = ctk.CTkToplevel(self)
        login_window.title("DJwerk - Connect to Tidal")
        login_window.geometry("500x400")
        login_window.configure(fg_color=DARK_GREY)
        login_window.attributes("-topmost", True)
        
        ctk.CTkLabel(login_window, text="🔗 Connect Tidal DJ Account", font=ctk.CTkFont(size=20, weight="bold"), text_color=ORANGE).pack(pady=(30, 10))
        ctk.CTkLabel(login_window, text="Activate this device to sync lossless tracks directly.", font=ctk.CTkFont(size=12), text_color="#aaaaaa").pack(pady=(0, 30))
        
        ctk.CTkLabel(login_window, text="Go to:", font=ctk.CTkFont(size=14)).pack()
        link_btn = ctk.CTkButton(login_window, text=link, fg_color="transparent", text_color=ORANGE, hover_color=MID_GREY, command=self.open_downloads)
        link_btn.pack(pady=(0, 20))
        
        ctk.CTkLabel(login_window, text="Enter this code:", font=ctk.CTkFont(size=14)).pack()
        code_label = ctk.CTkLabel(login_window, text=code, font=ctk.CTkFont(size=42, weight="bold"), text_color="#ffffff")
        code_label.pack(pady=20)
        
        ctk.CTkLabel(login_window, text="Waiting for authorization...", font=ctk.CTkFont(size=12, slant="italic"), text_color="#777777").pack()
        
        def check_status():
            # Check if login is now successful via the app's persistent handler
            if getattr(self, "tidal_logged_in", False):
                self.log_message(">> TIDAL: Authorization successful! Window closing...")
                login_window.destroy()
            else:
                # Re-check every second if the window still exists
                if login_window.winfo_exists():
                    login_window.after(1000, check_status)
            
        login_window.after(1000, check_status)
        return login_window

    def load_config(self):
        self.fx_enabled = False
        self.cookies_browser = "none"
        self.audio_quality = "High (FLAC)"
        self.pref_gain_enabled = False
        self.pref_gain_target = "-14 LUFS (Standard)"
        self.last_playlist_path = None
        self.playlist_history = []
        self.credentials = {
            "spotify_client_id": "",
            "spotify_client_secret": "",
            "bandcamp_username": ""
        }
        try:
            if os.path.exists(CONFIG_FILE):
                import json
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self.core.download_path = config.get("download_path", "downloads")
                    self.fx_enabled = config.get("fx_enabled", False)
                    self.cookies_browser = config.get("cookies_from_browser", "none")
                    self.audio_quality = config.get("audio_quality", "High (FLAC)")
                    self.pref_gain_enabled = config.get("pref_gain_enabled", False)
                    self.pref_gain_target = config.get("pref_gain_target", "-14 LUFS (Standard)")
                    self.last_playlist_path = config.get("last_playlist_path")
                    self.playlist_history = config.get("playlist_history", [])
                    self.credentials.update(config.get("credentials", {}))
        except Exception as e:
            print(f"Error loading config: {e}")

    def save_config(self, new_path=None, cookies_browser=None, credentials=None, last_playlist_path=None, playlist_history=None):
        try:
            config = {
                "download_path": new_path or self.core.download_path,
                "fx_enabled": self.fx_enabled,
                "cookies_from_browser": cookies_browser or self.cookies_browser,
                "audio_quality": self.audio_quality,
                "pref_gain_enabled": getattr(self, "pref_gain_enabled", False),
                "pref_gain_target": getattr(self, "pref_gain_target", "-14 LUFS (Standard)"),
                "last_playlist_path": last_playlist_path or self.last_playlist_path,
                "playlist_history": playlist_history if playlist_history is not None else self.playlist_history,
                "credentials": credentials or self.credentials
            }
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            pass

    def _create_context_menu(self, widget):
        menu = tk.Menu(self, tearoff=0, bg=MID_GREY, fg="#ffffff", activebackground=ORANGE, activeforeground="black")
        
        def handle_paste():
            try:
                # Native clipboard pull via Tkinter root
                clip_text = self.clipboard_get()
                widget.insert('insert', clip_text)
            except:
                pass
                
        def handle_copy():
            try:
                clip_text = widget.get()
                self.clipboard_clear()
                self.clipboard_append(clip_text)
            except:
                pass

        def handle_cut():
            try:
                handle_copy()
                widget.delete(0, 'end')
            except:
                pass

        menu.add_command(label="Cut", command=handle_cut)
        menu.add_command(label="Copy", command=handle_copy)
        menu.add_command(label="Paste", command=handle_paste)
        
        def show_menu(event):
            menu.tk_popup(event.x_root, event.y_root)
            
        widget.bind("<Button-3>", show_menu)
        widget.bind("<Button-2>", lambda e: handle_paste())

    def _log_message(self, text):
        # Insert text and then apply tags if keywords are found
        self.crate_log.insert("end", text + "\n")
        
        # Color specific lines based on status
        line_count = int(self.crate_log.index("end-1c").split(".")[0]) - 1
        start_idx = f"{line_count}.0"
        end_idx = f"{line_count}.end"
        
        if "[ERROR]" in text or "[FATAL]" in text:
            self.crate_log.tag_add("ERROR", start_idx, end_idx)
        elif "[SUCCESS]" in text:
            self.crate_log.tag_add("SUCCESS", start_idx, end_idx)
        elif "[INFO]" in text:
            self.crate_log.tag_add("INFO", start_idx, end_idx)
        elif "[SYSTEM]" in text or "[PLAYLIST]" in text:
            self.crate_log.tag_add("SYSTEM", start_idx, end_idx)
            
        self.crate_log.see("end")
        
    def _get_last_log_line(self):
        return self.crate_log.get("end-2c linestart", "end-1c")
        
    def _replace_last_log_line(self, text):
        self.crate_log.delete("end-2c linestart", "end")
        self.crate_log.insert("end", "\n" + text + "\n")
        self.crate_log.see("end")

    def open_downloads(self):
        dl_path = self.core.download_path
        if platform.system() == "Windows":
            os.startfile(dl_path)
        elif platform.system() == "Darwin":
            subprocess.call(["open", dl_path])
        else:
            subprocess.call(["xdg-open", dl_path])

    def export_center_event(self):
        export_window = ExportCenterWindow(self)
        export_window.focus()
        return export_window

    def help_event(self):
        help_window = ctk.CTkToplevel(self)
        help_window.title("DJwerk - Help & Manual")
        help_window.geometry("700x600")
        help_window.configure(fg_color=DARK_GREY)
        help_window.attributes("-topmost", True)
        
        ctk.CTkLabel(help_window, text="📖 USER MANUAL", font=ctk.CTkFont(size=24, weight="bold"), text_color=ORANGE).pack(pady=20)
        
        scroll = ctk.CTkScrollableFrame(help_window, fg_color=GLOW_BLACK)
        scroll.pack(fill="both", expand=True, padx=20, pady=10)
        
        manual_text = """
1. SYNCING CONTENT
   - Paste a URL (Playlist, Album, Track) into the top bar.
   - Or use 'PASTE & SYNC' to process any text in your clipboard.
   - Select tracks in the popup and hit 'START SYNC'.

2. PLATFORM TIPS
   - TIDAL: Login via the popup or use your browser session.
   - SPOTIFY: Use YOLO mode or add API keys in 'Advanced' settings.
   - SOUNDCLOUD: Direct profile/set links work best.
   - BEATPORT: Direct links to tracks or your /library page.

3. SETTINGS & CONNECTIONS
   - Go to 'Connections' to select your primary browser.
   - Verify 'CONNECTED' status for each platform.
   - Use 'General' to set Normalization targets (LUFS/Peak).

4. EXPORTING
   - Use the 'EXPORT CENTER' to push tracks to Rekordbox, Engine DJ, etc.
   - Check the 'downloads/' folder for physical M3U8 files.
"""
        ctk.CTkLabel(scroll, text=manual_text, justify="left", anchor="w", font=ctk.CTkFont(family="Consolas", size=13), text_color="#ccc").pack(padx=20, pady=10, fill="x")
        ctk.CTkButton(help_window, text="CLOSE", command=help_window.destroy, fg_color="#444").pack(pady=20)

    def settings_event(self):
        settings_window = ctk.CTkToplevel(self)
        settings_window.title("DJwerk - Settings Cockpit")
        settings_window.geometry("600x650")
        settings_window.configure(fg_color=DARK_GREY)
        settings_window.attributes("-topmost", True)
        
        # Tabview for organization
        tabview = ctk.CTkTabview(settings_window, fg_color=MID_GREY, segmented_button_selected_color=ORANGE, segmented_button_selected_hover_color="#cc7000")
        tabview.pack(fill="both", expand=True, padx=20, pady=(10, 20))
        
        # TAB 1: GENERAL
        tab_general = tabview.add("General")
        ctk.CTkLabel(tab_general, text="Main Crate & UI Settings", font=ctk.CTkFont(size=16, weight="bold"), text_color=ORANGE).pack(pady=(10, 20))
        
        path_frame = ctk.CTkFrame(tab_general, fg_color="transparent")
        path_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(path_frame, text="Download Path:", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=(0, 10))
        path_entry = ctk.CTkEntry(path_frame, text_color="#ffffff", fg_color=GLOW_BLACK, border_color=ORANGE)
        path_entry.pack(side="left", expand=True, fill="x", padx=(0, 10))
        path_entry.insert(0, self.core.download_path)

        def browse_folder():
            from customtkinter import filedialog
            folder = filedialog.askdirectory(initialdir=self.core.download_path)
            if folder:
                path_entry.delete(0, 'end'); path_entry.insert(0, folder)

        ctk.CTkButton(path_frame, text="Browse", width=70, fg_color=MID_GREY, command=browse_folder).pack(side="right")

        # NIEUW: Smart Gain Control
        ctk.CTkLabel(tab_general, text="Smart Gain Control (Normalization)", font=ctk.CTkFont(size=14, weight="bold"), text_color=ORANGE).pack(pady=(20, 5))
        gain_frame = ctk.CTkFrame(tab_general, fg_color=GLOW_BLACK, corner_radius=10)
        gain_frame.pack(fill="x", padx=10, pady=5)
        
        g1 = ctk.CTkFrame(gain_frame, fg_color="transparent")
        g1.pack(fill="x", padx=10, pady=5)
        self.gain_enabled = ctk.BooleanVar(value=getattr(self, "pref_gain_enabled", False))
        ctk.CTkSwitch(g1, text="Enable Normalization", variable=self.gain_enabled, progress_color=ORANGE).pack(side="left")
        
        # PRO MODE: Interactive Numeric Values
        self.gain_target = ctk.StringVar(value=getattr(self, "pref_gain_target", "-14.0 LUFS"))
        
        def update_slider_from_var(val_str):
            try:
                val = float(val_str.split(" ")[0])
                self.gain_slider.set(val)
            except: pass

        def on_slider_move(val):
            if "LUFS" in self.gain_target.get():
                self.gain_target.set(f"{val:.1f} LUFS")
            else:
                self.gain_target.set(f"{val:.1f} dB")

        def toggle_mode():
            if "LUFS" in self.gain_target.get():
                self.gain_target.set("0.0 dB")
                self.gain_scroller.unit = "dB"; self.gain_scroller.min_val = -12.0; self.gain_scroller.max_val = 0.0; self.gain_scroller.step = 0.1
                self.gain_slider.configure(from_=-12.0, to=0.0, number_of_steps=120)
                self.gain_slider.set(0.0)
            else:
                self.gain_target.set("-14.0 LUFS")
                self.gain_scroller.unit = "LUFS"; self.gain_scroller.min_val = -24.0; self.gain_scroller.max_val = -6.0; self.gain_scroller.step = 0.5
                self.gain_slider.configure(from_=-24.0, to=-6.0, number_of_steps=36)
                self.gain_slider.set(-14.0)
        
        mode_btn = ctk.CTkButton(g1, text="Mode", width=60, fg_color=MID_GREY, command=toggle_mode)
        mode_btn.pack(side="right", padx=5)
        
        # Determine initial scroller settings
        is_db = "dB" in self.gain_target.get()
        unit = "dB" if is_db else "LUFS"
        min_v = -12.0 if is_db else -24.0
        max_v = 0.0 if is_db else -6.0
        step = 0.1 if is_db else 0.5
        
        self.gain_scroller = InteractiveValue(g1, self.gain_target, unit=unit, min_val=min_v, max_val=max_v, step=step, font=ctk.CTkFont(size=16, weight="bold"))
        self.gain_scroller.pack(side="right", padx=10)
        CTKToolTip(self.gain_scroller, "Scroll mouse wheel here for fine-tuning")

        # SLIDER & PRESETS
        s_frame = ctk.CTkFrame(gain_frame, fg_color="transparent")
        s_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.gain_slider = ctk.CTkSlider(s_frame, from_=min_v, to=max_v, button_color=ORANGE, button_hover_color="#cc7000", progress_color=ORANGE, command=on_slider_move)
        self.gain_slider.pack(fill="x", side="left", expand=True, padx=10)
        update_slider_from_var(self.gain_target.get())

        presets_frame = ctk.CTkFrame(gain_frame, fg_color="transparent")
        presets_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        def set_preset(val):
            if "LUFS" in self.gain_target.get():
                self.gain_target.set(f"{val:.1f} LUFS")
            else:
                self.gain_target.set(f"{val:.1f} dB")
            self.gain_slider.set(val)

        ctk.CTkLabel(presets_frame, text="Presets:", font=ctk.CTkFont(size=11, slant="italic")).pack(side="left", padx=5)
        
        # Dynamic Presets based on mode
        def refresh_presets():
            for w in presets_container.winfo_children(): w.destroy()
            if "LUFS" in self.gain_target.get():
                ps = [(-14, "Spotify"), (-12, "Club"), (-9, "Loud")]
            else:
                ps = [(-6, "Classic"), (-1, "Safety"), (0, "Max")]
            for val, lbl in ps:
                ctk.CTkButton(presets_container, text=f"{val} ({lbl})", width=70, height=24, font=ctk.CTkFont(size=10), fg_color=MID_GREY, command=lambda v=val: set_preset(v)).pack(side="left", padx=2)

        presets_container = ctk.CTkFrame(presets_frame, fg_color="transparent")
        presets_container.pack(side="left")
        
        # Wrap toggle_mode to refresh presets
        orig_toggle = toggle_mode
        def toggle_with_presets():
            orig_toggle()
            refresh_presets()
        mode_btn.configure(command=toggle_with_presets)
        refresh_presets()

        # TAB 2: CONNECTIONS (The chique browser-first approach)
        tab_conn = tabview.add("Connections")
        
        ctk.CTkLabel(tab_conn, text="🌐 Universal Browser Authentication", font=ctk.CTkFont(size=16, weight="bold"), text_color=ORANGE).pack(pady=(10, 5))
        ctk.CTkLabel(tab_conn, text="Select sources to use via browser cookies.", font=ctk.CTkFont(size=12), text_color="#aaaaaa").pack(pady=(0, 15))

        # Primary Browser Selection
        browser_frame = ctk.CTkFrame(tab_conn, fg_color=GLOW_BLACK, corner_radius=10)
        browser_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(browser_frame, text="Auth Browser:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=15, pady=15)
        
        def on_browser_change(choice):
            self.cookies_browser = choice
            self.event_generate("<<RefreshStatusesEvent>>")

        browser_options = ["none", "chrome", "firefox", "safari", "edge", "opera", "vivaldi", "brave"]
        browser_menu = ctk.CTkOptionMenu(browser_frame, values=browser_options, fg_color=MID_GREY, button_color=ORANGE, button_hover_color="#cc7000", command=on_browser_change)
        browser_menu.pack(side="left", expand=True, fill="x", padx=10)
        browser_menu.set(self.cookies_browser)

        # Service Grid
        services_frame = ctk.CTkFrame(tab_conn, fg_color="transparent")
        services_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.service_status_labels = {}
        self.service_account_labels = {}
        self.source_vars = {}

        def draw_browser_service(parent, name, url):
            row = ctk.CTkFrame(parent, fg_color=MID_GREY, corner_radius=8, height=45)
            row.pack(fill="x", pady=4)
            
            # Source Enable Checkbox
            var = ctk.BooleanVar(value=True)
            self.source_vars[name.lower()] = var
            cb = ctk.CTkCheckBox(row, text=name, variable=var, font=ctk.CTkFont(weight="bold"), width=120, border_color=ORANGE, hover_color=ORANGE)
            cb.pack(side="left", padx=15)
            
            # Status Indicator
            status_label = ctk.CTkLabel(row, text="CHECKING...", text_color="#777777", font=ctk.CTkFont(size=11, weight="bold"))
            status_label.pack(side="left", padx=10)
            self.service_status_labels[name.lower()] = status_label

            # Account Name
            acc_label = ctk.CTkLabel(row, text="", text_color="#aaaaaa", font=ctk.CTkFont(size=10, slant="italic"))
            acc_label.pack(side="left", padx=10)
            self.service_account_labels[name.lower()] = acc_label
            
            def open_link():
                import webbrowser
                webbrowser.open(url)
            
            def logout_service():
                self.event_generate(f"<<Logout{name}Event>>")

            ctk.CTkButton(row, text="Logout", width=60, fg_color="#444", text_color="#aaa", command=logout_service).pack(side="right", padx=5, pady=5)
            ctk.CTkButton(row, text="Login", width=60, fg_color="transparent", border_width=1, border_color=ORANGE, command=open_link).pack(side="right", padx=5, pady=5)

        draw_browser_service(services_frame, "Tidal", "https://listen.tidal.com")
        draw_browser_service(services_frame, "Spotify", "https://open.spotify.com")
        draw_browser_service(services_frame, "Bandcamp", "https://bandcamp.com")
        draw_browser_service(services_frame, "SoundCloud", "https://soundcloud.com")
        draw_browser_service(services_frame, "Beatport", "https://www.beatport.com")

        def periodic_status_check():
            if settings_window.winfo_exists():
                self.event_generate("<<RefreshStatusesEvent>>")
                settings_window.after(3000, periodic_status_check)
        
        settings_window.after(100, periodic_status_check)

        # TAB 3: ADVANCED
        tab_adv = tabview.add("Advanced")
        ctk.CTkLabel(tab_adv, text="Manual API Keys (Optional)", font=ctk.CTkFont(size=14, weight="bold"), text_color=ORANGE).pack(pady=10)
        
        # Help link voor Spotify
        def open_spotify_dev():
            import webbrowser
            webbrowser.open("https://developer.spotify.com/dashboard")
            
        help_label = ctk.CTkLabel(tab_adv, text="Where do I find my Spotify Keys?", font=ctk.CTkFont(size=11, underline=True), text_color="#3498db", cursor="hand2")
        help_label.pack(pady=(0, 10))
        help_label.bind("<Button-1>", lambda e: open_spotify_dev())

        # Spotify ID
        ctk.CTkLabel(tab_adv, text="Spotify Client ID:", font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x", padx=20, pady=(10, 0))
        sp_id_entry = ctk.CTkEntry(tab_adv, placeholder_text="Enter ID...", border_color=ORANGE)
        sp_id_entry.pack(fill="x", padx=20, pady=(2, 5))
        sp_id_entry.insert(0, self.credentials.get("spotify_client_id", ""))
        
        # Spotify Secret
        ctk.CTkLabel(tab_adv, text="Spotify Client Secret:", font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x", padx=20, pady=(5, 0))
        sp_sec_entry = ctk.CTkEntry(tab_adv, placeholder_text="Enter Secret...", show="*")
        sp_sec_entry.pack(fill="x", padx=20, pady=(2, 5))
        sp_sec_entry.insert(0, self.credentials.get("spotify_client_secret", ""))
        
        # Bandcamp User
        ctk.CTkLabel(tab_adv, text="Bandcamp Username:", font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x", padx=20, pady=(5, 0))
        bc_user_entry = ctk.CTkEntry(tab_adv, placeholder_text="Enter Username...")
        bc_user_entry.pack(fill="x", padx=20, pady=(2, 10))
        bc_user_entry.insert(0, self.credentials.get("bandcamp_username", ""))

        def save_and_close():
            self.core.download_path = path_entry.get().strip()
            self.cookies_browser = browser_menu.get()
            self.pref_gain_enabled = self.gain_enabled.get()
            self.pref_gain_target = self.gain_target.get()
            
            self.credentials["spotify_client_id"] = sp_id_entry.get().strip()
            self.credentials["spotify_client_secret"] = sp_sec_entry.get().strip()
            self.credentials["bandcamp_username"] = bc_user_entry.get().strip()
            
            # NEW: Store enabled sources (simple list for now)
            self.enabled_sources = [name for name, var in self.source_vars.items() if var.get()]
            
            self.save_config()
            self.event_generate("<<SettingsUpdated>>")
            settings_window.destroy()

        ctk.CTkButton(settings_window, text="SAVE SETTINGS", fg_color=ORANGE, text_color="black", font=ctk.CTkFont(weight="bold"), command=save_and_close).pack(pady=20)
        ctk.CTkButton(settings_window, text="CLOSE", fg_color="#444", command=settings_window.destroy).pack(side="bottom", pady=10)
