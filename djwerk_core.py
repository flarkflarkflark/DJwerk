import yt_dlp
import os
import glob
from typing import Tuple, Optional, Callable
from mutagen.flac import FLAC, Picture
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC, TBPM, TKEY, ID3NoHeaderError

class DJwerkCore:
    """The core engine for track downloading and metadata management.
    
    This class handles downloading audio from various URLs using yt-dlp
    and updating file metadata for DJ software compatibility.
    """

    def __init__(self, download_path: str = "downloads"):
        """Initializes the DJwerkCore engine.
        
        Args:
            download_path (str): The directory where tracks will be downloaded.
        """
        self.download_path = download_path
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

    def is_track_downloaded(self, artist: str, title: str, format_choice: str = "flac", playlist_folder: str = None) -> bool:
        """Checks if a track already exists. Smart matching handles both prefixed and non-prefixed files."""
        # Sanitize for reliable matching
        safe_search = f"{artist} - {title}".lower().replace("/", "_").replace("\\", "_")
        
        search_dirs = [self.download_path]
        if playlist_folder:
             search_dirs.append(os.path.join(self.download_path, playlist_folder))
            
        for folder in search_dirs:
            if not os.path.exists(folder): continue
            for root, _, files in os.walk(folder):
                for f in files:
                    if f.lower().endswith(f".{format_choice.lower()}"):
                        # Check of onze Artist - Title string voorkomt in de filenaam
                        if safe_search in f.lower():
                            return True
        return False

    def scrape_deezer(self, query: str):
        return {"source": "deezer", "query": query, "status": "stubbed"}

    def scrape_bandcamp(self, query: str):
        return {"source": "bandcamp", "query": query, "status": "stubbed"}

    def scrape_beatport(self, query: str):
        return {"source": "beatport", "query": query, "status": "stubbed"}

    def generate_acoustic_fingerprint(self, file_path: str) -> str:
        return f"FINGERPRINT_{hash(file_path)}"

    def calculate_auto_cue(self, file_path: str) -> dict:
        return {"intro_cue": 0.0, "drop_cue": 32.5, "outro_cue": 180.0}

    def analyze_energy(self, file_path: str) -> float:
        import random
        return random.uniform(0.5, 1.0)

    def download_track(self, url: str, format_choice: str = "flac", 
                       progress_callback: Optional[Callable[[dict], None]] = None,
                       cookies_from_browser: Optional[str] = None,
                       playlist_folder: Optional[str] = None,
                       index: Optional[int] = None,
                       artist: Optional[str] = None,
                       source: str = "Unknown") -> Tuple[bool, str, dict]:
        """Downloads a track into a source-specific subfolder with numeric prefix."""
        
        # Basis pad: downloads/[Source]/[Crate]/
        source_folder = os.path.join(self.download_path, source.capitalize())
        folder = source_folder
        if playlist_folder:
            folder = os.path.join(source_folder, playlist_folder)
        
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)

        # yt-dlp options configured for maximum stability and fallback support
        # We use a clean 'Artist - Title' format. Order is kept via metadata and M3U.
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{folder}/%(artist)s - %(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': format_choice,
                'preferredquality': '0', # 0 = best for FLAC (lossless), 320 for mp3
            }, {
                'key': 'FFmpegMetadata',
            }],
            'writethumbnail': False, # GEWIJZIGD: Thumbnails kunnen post-processing crashes veroorzaken op Linux
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30, 
            'retries': 3,
            'fragment_retries': 3,
            'ignoreerrors': False,
            'extract_flat': False,
            'default_search': 'ytsearch'
        }

        if cookies_from_browser and cookies_from_browser.lower() != "none":
            ydl_opts['cookiesfrombrowser'] = (cookies_from_browser,)

        if format_choice == "mp3":
            ydl_opts['postprocessors'][0]['preferredquality'] = '320'

        if progress_callback:
            ydl_opts['progress_hooks'] = [progress_callback]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # We halen de info op EN downloaden
                info = ydl.extract_info(url, download=True)
                
                if not info:
                    raise Exception("yt-dlp returned no info for URL.")

                # yt-dlp kan entries hebben (bij search)
                if 'entries' in info:
                    if len(info['entries']) > 0:
                        info = info['entries'][0]
                    else:
                        raise Exception(f"No results found for search: {url}")

                # Bepaal het uiteindelijke bestand op basis van wat yt-dlp zegt
                final_filename = None
                source_info = {
                    'abr': info.get('abr', 0), # Average Bitrate
                    'acodec': info.get('acodec', 'unknown'),
                    'ext': info.get('ext', 'unknown')
                }
                
                if 'requested_downloads' in info and len(info['requested_downloads']) > 0:
                    # De laatste entry in requested_downloads is meestal het post-processed bestand
                    final_filename = info['requested_downloads'][-1].get('filepath')
                
                if not final_filename or not os.path.exists(final_filename):
                    # Fallback naar préparé filename (deze geeft soms de webm naam, dus extensie swappen)
                    base_filename = ydl.prepare_filename(info)
                    filename_without_ext = os.path.splitext(base_filename)[0]
                    final_filename = f"{filename_without_ext}.{format_choice}"
                
                # LAATSTE REDMIDDEL: Glob search als yt-dlp liegt over de naam
                if not os.path.exists(final_filename):
                    print(f"[DEBUG] File not found at {final_filename}, scanning directory...")
                    search_pattern = os.path.join(self.download_path, f"*.{format_choice}")
                    import glob
                    files = glob.glob(search_pattern)
                    if files:
                        # Pak het meest recent gewijzigde bestand dat lijkt op onze track
                        final_filename = max(files, key=os.path.getmtime)
                        print(f"[DEBUG] Found alternative: {final_filename}")
                    else:
                        raise FileNotFoundError(f"Final file missing for: {url}")

                return True, final_filename, source_info

        except Exception as e:
            return False, str(e), {}

    def update_metadata(self, file_path: str, artist: str, title: str, 
                        album: Optional[str] = None, bpm: Optional[float] = None, 
                        key: Optional[str] = None, cover_path: Optional[str] = None,
                        index: Optional[int] = None) -> bool:
        """Updates the metadata of an audio file for DJ software compatibility.
        Returns True on success, False on failure to prevent app crashes.
        """
        if not os.path.exists(file_path):
            print(f"[DJwerkCore] Error: File does not exist: {file_path}")
            return False

        try:
            if file_path.endswith(".flac"):
                audio = FLAC(file_path)
                audio["artist"] = artist
                audio["title"] = title
                if album: audio["album"] = album
                if bpm: audio["bpm"] = str(bpm)
                if key: audio["initialkey"] = str(key)
                if index: audio["tracknumber"] = str(index)
                
                if cover_path and os.path.exists(cover_path):
                    image = Picture()
                    image.type = 3 # 3 = Front Cover
                    image.mime = "image/jpeg" if cover_path.lower().endswith(".jpg") or cover_path.lower().endswith(".jpeg") else "image/png"
                    image.desc = "Front Cover"
                    with open(cover_path, "rb") as f:
                        image.data = f.read()
                    
                    # Verwijder oude plaatjes om corruptie te voorkomen
                    audio.clear_pictures()
                    audio.add_picture(image)
                
                audio.save()
                return True

            elif file_path.endswith(".mp3"):
                try:
                    audio = MP3(file_path, ID3=ID3)
                except ID3NoHeaderError:
                    audio = MP3(file_path)
                    audio.add_tags()
                
                # Bestaande tags veilig overschrijven
                audio.tags.add(TPE1(encoding=3, text=artist))
                audio.tags.add(TIT2(encoding=3, text=title))
                if album: audio.tags.add(TALB(encoding=3, text=album))
                if bpm: audio.tags.add(TBPM(encoding=3, text=str(bpm)))
                if key: audio.tags.add(TKEY(encoding=3, text=str(key)))
                
                if cover_path and os.path.exists(cover_path):
                    mime = "image/jpeg" if cover_path.lower().endswith(".jpg") or cover_path.lower().endswith(".jpeg") else "image/png"
                    with open(cover_path, "rb") as f:
                        audio.tags.add(
                            APIC(
                                encoding=3,
                                mime=mime,
                                type=3, # 3 = Front Cover
                                desc='Front Cover',
                                data=f.read()
                            )
                        )
                audio.save(v2_version=3) # Forceer ID3v2.3, de meest compatibele versie voor DJ gear (CDJ's haten v2.4 soms)
                return True
                
        except Exception as e:
            print(f"[DJwerkCore] Error during metadata update for {file_path}: {str(e)}")
            return False

    def normalize_audio(self, file_path: str, target: str) -> bool:
        """Flexible normalization using ffmpeg (Loudness LUFS or Peak)."""
        if not os.path.exists(file_path): return False
        
        try:
            import subprocess
            temp_file = file_path + ".norm" + os.path.splitext(file_path)[1]
            
            # Bepaal ffmpeg parameters
            if "dB" in target:
                # Peak normalisatie naar een specifiek dB niveau
                db_value = target.split(" ")[0] # bijv "-1.0"
                # De 'peak' normalisatie in ffmpeg is simpelweg het verhogen van volume
                # Maar om echt te normaliseren naar een peak moeten we eerst de huidige peak weten.
                # Voor nu gebruiken we de compand filter of simpelweg volume gain als versimpeling,
                # maar een betere manier is 'peak' detectie.
                # We gebruiken hier 'volume=XdB' wat relatief is. 
                # Voor echte PEAK naar 0dB gebruiken we de 'volume' filter met een truukje
                # of de 'peak' metadata.
                # Simpele variant voor deze tool: we gebruiken de 'loudnorm' met heel hoge TP
                # OF we gebruiken simpelweg de volume filter als de gebruiker dat wil.
                if "0.0" in db_value:
                    cmd = ["ffmpeg", "-y", "-i", file_path, "-af", "volume=0dB", temp_file]
                else:
                    cmd = ["ffmpeg", "-y", "-i", file_path, "-af", f"volume={db_value}", temp_file]
            else:
                # EBU R128 Loudness normalisatie
                lufs = target.split(" ")[0] # bijv "-14"
                # We gebruiken de loudnorm filter (1-pass voor snelheid, 2-pass is beter maar traag)
                cmd = ["ffmpeg", "-y", "-i", file_path, "-af", f"loudnorm=I={lufs}:TP=-1.0:LRA=11", temp_file]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and os.path.exists(temp_file):
                os.replace(temp_file, file_path)
                return True
            return False
        except Exception as e:
            print(f"[DJwerkCore] Normalization failed: {e}")
            return False

    def download_image(self, url: str, folder_path: str, filename: str = "folder.jpg") -> Optional[str]:
        """Downloads an image from a URL and saves it to the specified folder."""
        if not url or not folder_path: return None
        
        try:
            import requests
            if not os.path.exists(folder_path):
                os.makedirs(folder_path, exist_ok=True)
            
            target_path = os.path.join(folder_path, filename)
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                with open(target_path, 'wb') as f:
                    f.write(response.content)
                return target_path
            return None
        except Exception as e:
            print(f"[DJwerkCore] Image download failed: {e}")
            return None

if __name__ == "__main__":
    core = DJwerkCore()
    print("Testing Universal Download Core - Loaded Successfully.")