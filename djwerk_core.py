import yt_dlp
import os
import glob
import re
import uuid
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

    LOSSLESS_CODECS = {"flac", "alac", "wav", "aiff", "pcm", "ape", "wv"}
    LOSSLESS_EXTS = {"flac", "alac", "wav", "aiff", "aif", "ape", "wv"}

    def _clean_metadata_value(self, value: Optional[str], fallback: str) -> str:
        if value is None:
            return fallback
        cleaned = str(value).strip()
        if not cleaned:
            return fallback
        lowered = cleaned.lower()
        if lowered in {"na", "n/a", "unknown", "unknown artist", "unknown title"}:
            return fallback
        return cleaned

    def _sanitize_filename_part(self, value: str) -> str:
        # Remove characters that are invalid across Windows/macOS/Linux filesystems
        # while preserving case and readable punctuation.
        cleaned = str(value)
        cleaned = "".join(ch for ch in cleaned if ch >= " " and ch != "\x7f")
        cleaned = cleaned.replace("/", " - ").replace("\\", " - ")
        cleaned = re.sub(r'[<>:"|?*]', "_", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = re.sub(r"\s+-\s+", " - ", cleaned)
        cleaned = re.sub(r"_+", "_", cleaned)
        cleaned = cleaned.strip(" ._")
        return cleaned or "Unknown"

    def _build_canonical_filename(self, artist: Optional[str], title: Optional[str],
                                  index: Optional[int], index_width: Optional[int],
                                  extension: str) -> str:
        safe_artist = self._sanitize_filename_part(self._clean_metadata_value(artist, "Unknown Artist"))
        safe_title = self._sanitize_filename_part(self._clean_metadata_value(title, "Unknown Title"))
        prefix = f"{index:0{index_width}d} - " if index is not None and index_width else ""
        return f"{prefix}{safe_artist} - {safe_title}.{extension.lstrip('.')}"

    def _ensure_unique_path(self, path: str) -> str:
        if not os.path.exists(path):
            return path
        base, ext = os.path.splitext(path)
        counter = 1
        while True:
            candidate = f"{base} ({counter}){ext}"
            if not os.path.exists(candidate):
                return candidate
            counter += 1

    def _unwrap_info_entry(self, info: dict) -> dict:
        if info and "entries" in info and info["entries"]:
            return info["entries"][0] or info
        return info or {}

    def _select_format_info(self, info: dict) -> dict:
        if info.get("requested_formats"):
            return info["requested_formats"][-1]
        fmt_id = info.get("format_id")
        if fmt_id and info.get("formats"):
            for fmt in info["formats"]:
                if fmt.get("format_id") == fmt_id:
                    return fmt
        return info

    def _build_source_info(self, info: dict) -> dict:
        info = self._unwrap_info_entry(info)
        fmt_info = self._select_format_info(info)
        acodec = (fmt_info.get("acodec") or info.get("acodec") or "unknown").lower()
        ext = (fmt_info.get("ext") or info.get("ext") or "unknown").lower()
        abr = fmt_info.get("abr") or info.get("abr") or fmt_info.get("tbr") or info.get("tbr") or 0
        try:
            abr = float(abr) if abr else 0
        except (TypeError, ValueError):
            abr = 0
        asr = fmt_info.get("asr") or info.get("asr")
        bit_depth = fmt_info.get("audio_bit_depth") or info.get("audio_bit_depth") or fmt_info.get("bit_depth") or info.get("bit_depth")
        source_is_lossless = acodec in self.LOSSLESS_CODECS or ext in self.LOSSLESS_EXTS
        source_is_true_320 = acodec == "mp3" and abr >= 320
        return {
            "acodec": acodec,
            "ext": ext,
            "abr": abr,
            "asr": asr,
            "bit_depth": bit_depth,
            "source_is_lossless": source_is_lossless,
            "source_is_true_320": source_is_true_320,
        }

    def _quality_policy_decision(self, requested_format: str, source_info: dict, policy: dict,
                                 needs_probe: bool = False) -> dict:
        requested = (requested_format or "").lower()
        require_lossless_flac = policy.get("require_lossless_for_flac", True)
        require_lossless_or_320 = policy.get("require_lossless_or_320_for_mp3", True)
        on_mismatch = policy.get("on_mismatch", "skip")

        lossless = source_info.get("source_is_lossless", False)
        true_320 = source_info.get("source_is_true_320", False)

        decision = {"action": "accept", "transcode": requested, "reason": ""}
        if needs_probe:
            decision["action"] = "probe"
            decision["reason"] = "source unknown / unverifiable"
            decision["transcode"] = None
            return decision
        if requested == "flac":
            if require_lossless_flac and not lossless:
                if on_mismatch == "skip":
                    decision["action"] = "reject"
                else:
                    decision["action"] = "source"
                    decision["transcode"] = None
                decision["reason"] = "source not verified lossless"
            else:
                decision["transcode"] = "flac" if not (source_info.get("ext") == "flac" or source_info.get("acodec") == "flac") else None
        elif requested == "mp3":
            if require_lossless_or_320 and not (lossless or true_320):
                if on_mismatch == "skip":
                    decision["action"] = "reject"
                else:
                    decision["action"] = "source"
                    decision["transcode"] = None
                decision["reason"] = "no uptranscode allowed"
            else:
                decision["transcode"] = "mp3" if not true_320 else None
        else:
            decision["transcode"] = None
        return decision

    def _format_requested_label(self, requested_format: Optional[str], requested_label: Optional[str]) -> str:
        if requested_label:
            return requested_label
        requested = (requested_format or "").lower()
        if requested == "mp3":
            return "MP3 320"
        if requested == "flac":
            return "FLAC"
        if requested == "source" or not requested:
            return "SOURCE"
        return requested_format.upper()

    def _format_quality_logs(self, requested_label: str, source_info: dict, decision: dict) -> list:
        abr = source_info.get("abr", 0)
        abr_str = f"{abr:.0f} kbps" if abr else "unknown kbps"
        lossless_tag = "lossless" if source_info.get("source_is_lossless") else "lossy"
        asr = source_info.get("asr")
        bit_depth = source_info.get("bit_depth")
        extra = []
        if bit_depth:
            extra.append(f"{bit_depth}-bit")
        if asr:
            extra.append(f"{asr} Hz")
        extra_str = f" ({', '.join(extra)})" if extra else ""
        decision_text = decision.get("action", "").upper()
        logs = [
            f"[QUALITY] Requested: {requested_label}",
            f"[QUALITY] Source: {source_info.get('acodec', 'unknown').upper()} {abr_str} ({source_info.get('ext', 'unknown')}) {lossless_tag}{extra_str}".strip(),
            f"[QUALITY] Decision: {decision_text}",
        ]
        if decision.get("reason"):
            logs.append(f"[QUALITY] Reason: {decision['reason']}")
        return logs

    def _run_subprocess(self, cmd):
        import subprocess
        run_kwargs = {"capture_output": True, "text": True}
        if os.name == "nt":
            run_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
            run_kwargs["startupinfo"] = startupinfo
        return subprocess.run(cmd, **run_kwargs)

    def _probe_audio_file(self, file_path: str) -> dict:
        import json
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-select_streams", "a:0",
                "-show_entries", "stream=codec_name,bit_rate,sample_rate,bits_per_raw_sample,bits_per_sample",
                "-of", "json",
                file_path
            ]
            result = self._run_subprocess(cmd)
            if result.returncode == 0 and result.stdout:
                data = json.loads(result.stdout)
                stream = (data.get("streams") or [{}])[0]
                acodec = (stream.get("codec_name") or "unknown").lower()
                try:
                    abr = float(stream.get("bit_rate", 0)) / 1000.0
                except (TypeError, ValueError):
                    abr = 0
                try:
                    asr = int(stream.get("sample_rate")) if stream.get("sample_rate") else None
                except (TypeError, ValueError):
                    asr = None
                bit_depth = stream.get("bits_per_raw_sample") or stream.get("bits_per_sample")
                ext = os.path.splitext(file_path)[1].lstrip(".").lower() or "unknown"
                source_is_lossless = acodec in self.LOSSLESS_CODECS or ext in self.LOSSLESS_EXTS
                source_is_true_320 = acodec == "mp3" and abr >= 320
                return {
                    "acodec": acodec,
                    "ext": ext,
                    "abr": abr,
                    "asr": asr,
                    "bit_depth": bit_depth,
                    "source_is_lossless": source_is_lossless,
                    "source_is_true_320": source_is_true_320,
                }
        except Exception:
            pass

        # Fallback: try mutagen
        try:
            from mutagen import File
            audio = File(file_path)
            if audio and getattr(audio, "info", None):
                info = audio.info
                abr = getattr(info, "bitrate", 0) / 1000.0 if getattr(info, "bitrate", 0) else 0
                asr = getattr(info, "sample_rate", None)
                ext = os.path.splitext(file_path)[1].lstrip(".").lower() or "unknown"
                acodec = (audio.mime[0].split("/")[-1] if getattr(audio, "mime", None) else "unknown").lower()
                source_is_lossless = acodec in self.LOSSLESS_CODECS or ext in self.LOSSLESS_EXTS
                source_is_true_320 = acodec == "mp3" and abr >= 320
                return {
                    "acodec": acodec,
                    "ext": ext,
                    "abr": abr,
                    "asr": asr,
                    "bit_depth": getattr(info, "bits_per_sample", None),
                    "source_is_lossless": source_is_lossless,
                    "source_is_true_320": source_is_true_320,
                }
        except Exception:
            pass

        return {}

    def _transcode_audio(self, source_path: str, target_ext: str) -> Optional[str]:
        target_ext = target_ext.lower()
        temp_out = f"{source_path}.transcode.{target_ext}"
        if target_ext == "mp3":
            cmd = ["ffmpeg", "-y", "-i", source_path, "-b:a", "320k", temp_out]
        elif target_ext == "flac":
            cmd = ["ffmpeg", "-y", "-i", source_path, temp_out]
        else:
            return None
        result = self._run_subprocess(cmd)
        if result.returncode == 0 and os.path.exists(temp_out):
            return temp_out
        if os.path.exists(temp_out):
            try:
                os.remove(temp_out)
            except Exception:
                pass
        return None

    def preflight_quality(self, url: str, requested_format: str, cookies_from_browser: Optional[str],
                          policy: dict, requested_label: Optional[str] = None) -> dict:
        preflight_info = {}
        try:
            pre_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'skip_download': True,
            }
            if cookies_from_browser and cookies_from_browser.lower() != "none":
                pre_opts['cookiesfrombrowser'] = (cookies_from_browser,)
            with yt_dlp.YoutubeDL(pre_opts) as pre_ydl:
                preflight_info = pre_ydl.extract_info(url, download=False) or {}
        except Exception:
            preflight_info = {}

        source_info = self._build_source_info(preflight_info)
        needs_probe = source_info.get("acodec") == "unknown" or source_info.get("ext") == "unknown"
        if requested_format == "mp3" and not source_info.get("abr"):
            needs_probe = True
        decision = self._quality_policy_decision(requested_format, source_info, policy, needs_probe=needs_probe)
        label = self._format_requested_label(requested_format, requested_label)
        logs = self._format_quality_logs(label, source_info, decision)
        return {
            "preflight_info": preflight_info,
            "source_info": source_info,
            "decision": decision,
            "logs": logs,
            "needs_probe": needs_probe,
        }

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
                       index_width: Optional[int] = None,
                       artist: Optional[str] = None,
                       title: Optional[str] = None,
                       source: str = "Unknown",
                       quality_policy: Optional[dict] = None,
                       requested_label: Optional[str] = None,
                       preflight_result: Optional[dict] = None) -> Tuple[bool, str, dict]:
        """Downloads a track into a source-specific subfolder with numeric prefix."""
        
        # Basis pad: downloads/[Source]/[Crate]/
        source_folder = os.path.join(self.download_path, source.capitalize())
        folder = source_folder
        if playlist_folder:
            folder = os.path.join(source_folder, playlist_folder)
        
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)

        # Build a canonical name from DJwerk metadata and download to a temp name first.
        pad_width = index_width if index_width else 2
        canonical_name = self._build_canonical_filename(artist, title, index, pad_width, format_choice)
        canonical_stem = os.path.splitext(canonical_name)[0]
        temp_base = os.path.join(folder, f".djwerk_tmp_{uuid.uuid4().hex}")
        outtmpl = f"{temp_base}.%(ext)s"

        policy = quality_policy or {
            "require_lossless_for_flac": True,
            "require_lossless_or_320_for_mp3": True,
            "on_mismatch": "skip",
        }
        if preflight_result is None:
            preflight_result = self.preflight_quality(
                url, format_choice, cookies_from_browser, policy, requested_label=requested_label
            )
        preflight_info = preflight_result.get("preflight_info", {})
        source_info = preflight_result.get("source_info", {})
        decision = preflight_result.get("decision", {})
        quality_logs = list(preflight_result.get("logs", []))
        needs_probe = preflight_result.get("needs_probe", False)
        requested_label = self._format_requested_label(format_choice, requested_label)

        source_info["quality_logs"] = quality_logs
        source_info["quality_decision"] = decision.get("action")
        source_info["quality_reason"] = decision.get("reason")

        if decision.get("action") == "reject":
            return False, f"Quality policy rejected: {decision.get('reason') or 'unknown'}", source_info

        postprocessors = []
        if decision.get("transcode"):
            postprocessors.append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': decision["transcode"],
                'preferredquality': '0', # 0 = best for FLAC (lossless), 320 for mp3
            })
        # Metadata postprocessor not needed; tags are applied later via mutagen.

        # yt-dlp options configured for maximum stability and fallback support
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': outtmpl,
            'postprocessors': postprocessors,
            'writethumbnail': False,
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
            'retries': 5,
            'fragment_retries': 5,
            'ignoreerrors': True,
            'extract_flat': False,
            'default_search': 'ytsearch'
        }

        if cookies_from_browser and cookies_from_browser.lower() != "none":
            ydl_opts['cookiesfrombrowser'] = (cookies_from_browser,)

        if decision.get("transcode") == "mp3":
            ydl_opts['postprocessors'][0]['preferredquality'] = '320'

        if progress_callback:
            ydl_opts['progress_hooks'] = [progress_callback]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # We halen de info op EN downloaden
                info = ydl.extract_info(url, download=True)
                
                if not info:
                    # Try one more time with zero format restrictions if it's a search
                    if "ytsearch" in url:
                        ydl_opts['format'] = 'best'
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl2:
                            info = ydl2.extract_info(url, download=True)
                    
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
                source_info.update({
                    'abr': info.get('abr', source_info.get('abr', 0)),
                    'acodec': info.get('acodec', source_info.get('acodec', 'unknown')),
                    'ext': info.get('ext', source_info.get('ext', 'unknown'))
                })
                
                if 'requested_downloads' in info and len(info['requested_downloads']) > 0:
                    final_filename = info['requested_downloads'][-1].get('filepath')
                
                if not final_filename or not os.path.exists(final_filename):
                    expected_output = f"{temp_base}.{format_choice}"
                    if os.path.exists(expected_output):
                        final_filename = expected_output
                    else:
                        # Fallback naar préparé filename
                        base_filename = ydl.prepare_filename(info)
                        filename_without_ext = os.path.splitext(base_filename)[0]
                        # Check of er een bestand is met de gewenste extensie
                        potential = f"{filename_without_ext}.{format_choice}"
                        if os.path.exists(potential):
                            final_filename = potential
                        else:
                            # Scan de folder voor de meest logische match
                            search_pattern = f"{filename_without_ext}*"
                            matches = glob.glob(search_pattern)
                            if matches:
                                # Pak het bestand dat eindigt op onze format_choice of gewoon de grootste
                                best_match = next((m for m in matches if m.endswith(format_choice)), matches[0])
                                final_filename = best_match
                
                if not final_filename or not os.path.exists(final_filename):
                    raise FileNotFoundError(f"Final file missing for: {url}")

                final_path = final_filename
                final_ext = os.path.splitext(final_path)[1].lstrip(".") or format_choice

                if decision.get("action") == "probe" or needs_probe:
                    probe_info = self._probe_audio_file(final_path)
                    if probe_info:
                        source_info.update(probe_info)
                        decision = self._quality_policy_decision(format_choice, source_info, policy, needs_probe=False)
                    else:
                        on_mismatch = policy.get("on_mismatch", "skip")
                        decision = {
                            "action": "reject" if on_mismatch == "skip" else "source",
                            "transcode": None,
                            "reason": "source unknown / unverifiable",
                        }
                    quality_logs.append("[QUALITY] Recheck: probing downloaded source")
                    quality_logs.extend(self._format_quality_logs(requested_label, source_info, decision))
                    source_info["quality_logs"] = quality_logs
                    source_info["quality_decision"] = decision.get("action")
                    source_info["quality_reason"] = decision.get("reason")

                    if decision.get("action") == "reject":
                        try:
                            if os.path.exists(final_path):
                                os.remove(final_path)
                        except Exception:
                            pass
                        return False, f"Quality policy rejected: {decision.get('reason') or 'unknown'}", source_info

                    if decision.get("transcode"):
                        transcode_path = self._transcode_audio(final_path, decision["transcode"])
                        if transcode_path:
                            try:
                                os.remove(final_path)
                            except Exception:
                                pass
                            final_path = transcode_path
                            final_ext = os.path.splitext(final_path)[1].lstrip(".") or decision["transcode"]

                canonical_name = f"{canonical_stem}.{final_ext}"
                target_path = self._ensure_unique_path(os.path.join(folder, canonical_name))
                if os.path.abspath(final_path) != os.path.abspath(target_path):
                    os.replace(final_path, target_path)
                source_info['output_ext'] = final_ext
                return True, target_path, source_info

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

    def normalize_audio(self, file_path: str, target: str,
                        log_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Flexible normalization using ffmpeg (Loudness LUFS or Peak)."""
        if not os.path.exists(file_path): return False
        
        try:
            import subprocess
            import sys
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

            run_kwargs = {"capture_output": True, "text": True}
            if os.name == "nt":
                run_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
                run_kwargs["startupinfo"] = startupinfo

            result = subprocess.run(cmd, **run_kwargs)
            if result.returncode == 0 and os.path.exists(temp_file):
                os.replace(temp_file, file_path)
                return True

            error_text = (result.stderr or result.stdout or "").strip()
            if error_text:
                if log_callback:
                    log_callback(f">> [FFMPEG] {error_text}")
                print(error_text, file=sys.stderr)
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass
            return False
        except Exception as e:
            msg = f"[DJwerkCore] Normalization failed: {e}"
            if log_callback:
                log_callback(msg)
            print(msg)
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
