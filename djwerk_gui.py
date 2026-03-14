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
        
        self.logo_btn = ctk.CTkButton(self.sidebar, text="DJwerk", font=ctk.CTkFont(size=28, weight="bold"), text_color=ORANGE, fg_color="transparent", hover_color=MID_GREY, command=self.settings_event)
        self.logo_btn.pack(pady=30)

        self.sync_btn = ctk.CTkButton(self.sidebar, text="Sync Crate", fg_color=ORANGE, text_color="black", font=ctk.CTkFont(weight="bold"), command=lambda: self.event_generate("<<SyncEvent>>"))
        self.sync_btn.pack(padx=20, pady=10, fill="x")

        self.downloads_btn = ctk.CTkButton(self.sidebar, text="Open Downloads", fg_color="transparent", border_width=1, border_color=ORANGE, command=self.open_downloads)
        self.downloads_btn.pack(padx=20, pady=10, fill="x")

        self.settings_btn = ctk.CTkButton(self.sidebar, text="Settings", fg_color="transparent", command=self.settings_event)
        self.settings_btn.pack(side="bottom", pady=20)

        # Main Panel
        self.main_panel = ctk.CTkFrame(self, fg_color=DARK_GREY)
        self.main_panel.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_panel.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(self.main_panel, placeholder_text="Paste Tidal / Spotify / SoundCloud URL here...", height=45, border_color=ORANGE, fg_color=GLOW_BLACK, text_color="#ffffff", font=ctk.CTkFont(size=14))
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=20, pady=20)

        # Context menu
        self._create_context_menu(self.url_entry)

        self.glow_panel = ctk.CTkFrame(self.main_panel, height=300, corner_radius=20, fg_color=GLOW_BLACK, border_width=2, border_color="#333")
        self.glow_panel.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.visualizer_label = ctk.CTkLabel(self.glow_panel, text="[ FLARKING... ]", font=ctk.CTkFont(size=18, slant="italic"), text_color=ORANGE)
        self.visualizer_label.place(relx=0.5, rely=0.5, anchor="center")

        self.crate_log = ctk.CTkTextbox(self.main_panel, height=200, fg_color=GLOW_BLACK, text_color="#00FF00", font=ctk.CTkFont(family="Consolas", size=12))
        self.crate_log.grid(row=2, column=0, padx=20, pady=20, sticky="ew")
        
        self.log_message = self._log_message
        self.get_last_log_line = self._get_last_log_line
        self.replace_last_log_line = self._replace_last_log_line

    def load_config(self):
        self.fx_enabled = False # Standaard uit wegens trage VPS X11 connectie
        try:
            if os.path.exists(CONFIG_FILE):
                import json
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    if "download_path" in config:
                        self.core.download_path = config["download_path"]
                        if not os.path.exists(self.core.download_path):
                            os.makedirs(self.core.download_path)
                    if "fx_enabled" in config:
                        self.fx_enabled = config["fx_enabled"]
        except Exception as e:
            print(f"Error loading config: {e}")

    def save_config(self, new_path):
        try:
            config = {"download_path": new_path}
            with open(CONFIG_FILE, 'w') as f:
                json.write(config, f)
        except Exception as e:
            pass # Silent fail voor UI

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
        widget.bind("<Button-2>", show_menu)

    def _log_message(self, text):
        self.crate_log.insert("end", text + "\n")
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

    def settings_event(self):
        settings_window = ctk.CTkToplevel(self)
        settings_window.title("DJwerk - Settings Cockpit")
        settings_window.geometry("550x450")
        settings_window.configure(fg_color=DARK_GREY)
        settings_window.attributes("-topmost", True)
        
        settings_window.grab_set()

        ctk.CTkLabel(settings_window, text="Settings Cockpit", font=ctk.CTkFont(size=20, weight="bold"), text_color=ORANGE).pack(pady=(20, 5))
        ctk.CTkLabel(settings_window, text="Configure your Master Crate Directory & UI", font=ctk.CTkFont(size=12), text_color="#aaaaaa").pack(pady=(0, 20))
        
        path_frame = ctk.CTkFrame(settings_window, fg_color="transparent")
        path_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(path_frame, text="Download Path:", font=ctk.CTkFont(size=14, weight="bold"), text_color="#ffffff").pack(side="left", padx=(0, 10))
        
        path_entry = ctk.CTkEntry(path_frame, text_color="#ffffff", fg_color=GLOW_BLACK, border_color=ORANGE, placeholder_text="/home/user/Music/DJwerk")
        path_entry.pack(side="left", expand=True, fill="x", padx=(0, 10))
        path_entry.insert(0, self.core.download_path)

        def browse_folder():
            from customtkinter import filedialog
            folder = filedialog.askdirectory(initialdir=self.core.download_path, title="Select Master Crate Directory")
            if folder:
                path_entry.delete(0, 'end')
                path_entry.insert(0, folder)

        browse_btn = ctk.CTkButton(path_frame, text="Browse", width=70, fg_color=MID_GREY, hover_color=ORANGE, border_width=1, border_color=ORANGE, command=browse_folder)
        browse_btn.pack(side="right")

        # FX Toggle
        fx_frame = ctk.CTkFrame(settings_window, fg_color="transparent")
        fx_frame.pack(fill="x", padx=20, pady=10)
        fx_switch = ctk.CTkSwitch(fx_frame, text="Enable GUI Glow/Visualizer FX", text_color="#ffffff", font=ctk.CTkFont(size=14, weight="bold"), progress_color=ORANGE, button_color="#ffffff", button_hover_color="#dddddd")
        fx_switch.pack(side="left", padx=10)
        if self.fx_enabled:
            fx_switch.select()

        info_frame = ctk.CTkFrame(settings_window, fg_color=MID_GREY, corner_radius=10)
        info_frame.pack(fill="x", padx=20, pady=20)
        ctk.CTkLabel(info_frame, text="💡 Tip: Zet FX uit als je inlogt via een trage X11/SSH verbinding.\nDit voorkomt dat de terminal / log laggy wordt.", 
                     justify="left", text_color="#cccccc", font=ctk.CTkFont(size=11)).pack(padx=10, pady=10)

        def save_and_close():
            new_path = path_entry.get().strip()
            self.fx_enabled = bool(fx_switch.get())
            
            if new_path:
                self.core.download_path = new_path
                if not os.path.exists(new_path):
                    try:
                        os.makedirs(new_path)
                    except:
                        pass
                try:
                    with open(CONFIG_FILE, 'w') as f:
                        import json
                        json.dump({
                            "download_path": new_path,
                            "fx_enabled": self.fx_enabled
                        }, f, indent=4)
                    self.log_message(f">> SETTINGS: Saved. FX is {'AAN' if self.fx_enabled else 'UIT'}.")
                except Exception as e:
                    self.log_message(f">> SETTINGS ERROR: Could not save config. {e}")
            
            # Stuur een custom event naar de controller dat settings zijn geupdate
            self.event_generate("<<SettingsUpdated>>")
            settings_window.destroy()

        ctk.CTkButton(settings_window, text="Save & Close", fg_color=ORANGE, text_color="black", hover_color="#cc7000", font=ctk.CTkFont(weight="bold"), command=save_and_close).pack(pady=(0, 20))
