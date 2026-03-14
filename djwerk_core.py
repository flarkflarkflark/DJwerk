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

    def is_track_downloaded(self, artist: str, title: str, extension: str = "flac") -> bool:
        """Checks if a track already exists in the download directory."""
        safe_title = f"{artist} - {title}".replace("/", "_").replace("\\", "_")
        possible_file = os.path.join(self.download_path, f"{safe_title}.{extension}")
        
        if os.path.exists(possible_file):
            return True
        
        for f in os.listdir(self.download_path):
            if f.startswith(safe_title) and f.endswith(f".{extension}"):
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
                       progress_callback: Optional[Callable[[dict], None]] = None) -> Tuple[bool, str]:
        """Downloads a track from a given URL and ensures the final file is returned."""
        
        # yt-dlp options configured for maximum stability and fallback support
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{self.download_path}/%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': format_choice,
                'preferredquality': '0', # 0 = best for FLAC (lossless), 320 for mp3
            }, {
                'key': 'EmbedThumbnail',
            }, {
                'key': 'FFmpegMetadata',
            }],
            'writethumbnail': True,
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30, # Prevent hanging on dead connections
            'retries': 3,
            'fragment_retries': 3,
            'ignoreerrors': False,
            'extract_flat': False, # GEWIJZIGD: Flat voorkomt dat hij de uiteindelijke stream URL vindt bij search
            'default_search': 'ytsearch' # Voorkom YouTube captcha lock bij directe scrape
        }

        if format_choice == "mp3":
            ydl_opts['postprocessors'][0]['preferredquality'] = '320'

        if progress_callback:
            ydl_opts['progress_hooks'] = [progress_callback]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                # yt-dlp's prepare_filename gives the raw downloaded file (e.g. .webm or .m4a)
                # We need to calculate the final processed filename.
                base_filename = ydl.prepare_filename(info)
                filename_without_ext = os.path.splitext(base_filename)[0]
                final_filename = f"{filename_without_ext}.{format_choice}"
                
                # Soms voegt yt-dlp een rare hash toe of verandert de titel, check via glob als exact match faalt
                if not os.path.exists(final_filename):
                    search_pattern = f"{filename_without_ext}*.{format_choice}"
                    matches = glob.glob(search_pattern)
                    if matches:
                        final_filename = matches[0]
                    else:
                        raise FileNotFoundError(f"Post-processed file not found: {final_filename}")

                return True, final_filename

        except Exception as e:
            return False, str(e)

    def update_metadata(self, file_path: str, artist: str, title: str, 
                        album: Optional[str] = None, bpm: Optional[float] = None, 
                        key: Optional[str] = None, cover_path: Optional[str] = None) -> bool:
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

if __name__ == "__main__":
    core = DJwerkCore()
    print("Testing Universal Download Core - Loaded Successfully.")