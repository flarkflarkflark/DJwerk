import requests
import re
import json
import yt_dlp
import os
from typing import List, Dict
from tidal_api_handler import TidalApiHandler

class TidalCrateParser:
    def __init__(self, api_handler: TidalApiHandler = None):
        print("[MATCHER] Tidal Scraper Initialized.")
        self.api = api_handler or TidalApiHandler()

    def get_tracks(self, url: str, cookies_from_browser: str = "none") -> List[Dict]:
        """Parses metadata from Tidal links using a tiered approach (Official API -> JSON -> Meta)."""
        
        # 0. PROBEER OFFICIELE API (Indien ingelogd)
        if any(x in url for x in ["playlist/", "album/", "track/", "mix/"]):
            parts = url.split("/")
            # Vind de ID (het deel na de pattern)
            item_id = None
            for i, p in enumerate(parts):
                if p in ["playlist", "album", "track", "mix"]:
                    item_id = parts[i+1].split("?")[0]
                    break
            
            if item_id and self.api.check_login():
                if "mix/" in url:
                    print(f"[MATCHER] Using official Tidal API for Mix: {item_id}")
                    tracks = self.api.get_mix_tracks(item_id)
                else:
                    print(f"[MATCHER] Using official Tidal API for: {item_id}")
                    tracks = self.api.get_playlist_tracks(item_id)
                
                if tracks:
                    return tracks
        
        clean_url = url
        if "tidal.com" in url and all(x not in url for x in ["/browse/", "/playlist/", "/track/"]):
             clean_url = url.replace("tidal.com/", "tidal.com/browse/")

        print(f"[MATCHER] Scraping Tidal metadata: {clean_url} (Browser: {cookies_from_browser})")
        tracks = []

        # Tier 1: JSON Extraction (__NEXT_DATA__)
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            response = requests.get(clean_url, headers=headers, timeout=10)
            if response.status_code == 200:
                json_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">([^<]+)</script>', response.text)
                if json_match:
                    data = json.loads(json_match.group(1))
                    
                    # Probeer de overkoepelende titel te vinden (Playlist of Album naam)
                    overall_title = ""
                    try:
                        # Bij Tidal zit dit vaak diep in de props
                        overall_title = data.get('props', {}).get('pageProps', {}).get('playlist', {}).get('title', '')
                        if not overall_title:
                             overall_title = data.get('props', {}).get('pageProps', {}).get('album', {}).get('title', '')
                    except: pass

                    def find_tracks_recursive(obj):
                        found = []
                        if isinstance(obj, dict):
                            if obj.get('type') == 'track' or ('title' in obj and 'artists' in obj and 'duration' in obj):
                                artist = obj.get('artists', [{}])[0].get('name', obj.get('artist', {}).get('name', 'Unknown'))
                                found.append({
                                    'artist': artist,
                                    'title': obj.get('title', obj.get('name', 'Unknown')),
                                    'album': overall_title if overall_title else obj.get('album', {}).get('title', ''),
                                    'duration': obj.get('duration'),
                                    'is_lossless': True,
                                    'is_playlist': "playlist" in clean_url,
                                    'source': 'Tidal'
                                })
                            else:
                                for v in obj.values(): found.extend(find_tracks_recursive(v))
                        elif isinstance(obj, list):
                            for item in obj: found.extend(find_tracks_recursive(item))
                        return found
                    tracks = find_tracks_recursive(data)
                    if tracks:
                        print(f"[MATCHER] Tidal JSON Success: Found {len(tracks)} tracks.")
                        return tracks
        except: pass

        # Tier 2: Meta Description Fallback
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            response = requests.get(clean_url, headers=headers, timeout=10)
            desc_match = re.search(r'<meta name="description" content="([^"]+)"', response.text)
            if desc_match:
                desc_text = desc_match.group(1)
                if "Featuring:" in desc_text or "featuring" in desc_text.lower():
                    feat_part = desc_text.split("eaturing:")[1] if "eaturing:" in desc_text else desc_text.split("eaturing")[1]
                    for raw_t in feat_part.split(","):
                        if " by " in raw_t:
                            parts = raw_t.split(" by ")
                            tracks.append({
                                'artist': parts[1].replace(".", "").strip(),
                                'title': parts[0].strip(),
                                'album': '', 'is_lossless': True, 'is_playlist': True,
                                'source': 'Tidal'
                            })
            if tracks:
                print(f"[MATCHER] Tidal Meta Success: Found {len(tracks)} tracks.")
                return tracks
        except: pass

        # Tier 3: yt-dlp Fallback
        try:
            ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': False}
            if cookies_from_browser.lower() != "none": ydl_opts['cookiesfrombrowser'] = (cookies_from_browser,)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(clean_url, download=False)
                entries = info.get('entries', [info])
                for entry in entries:
                    if not entry: continue
                    tracks.append({
                        'artist': entry.get('artist', entry.get('uploader', 'Unknown Artist')),
                        'title': entry.get('title', 'Unknown Title'),
                        'album': info.get('title', '') if 'entries' in info else entry.get('album', ''),
                        'is_lossless': True, 'is_playlist': 'entries' in info,
                        'source': 'Tidal',
                        'duration': entry.get('duration')
                    })
        except: pass
            
        return tracks

class SpotifyCrateParser:
    def __init__(self, api_handler=None):
        print("[MATCHER] Spotify Scraper Initialized.")
        from spotify_api_handler import SpotifyApiHandler
        self.api = api_handler or SpotifyApiHandler()

    def get_tracks(self, url: str, cookies_from_browser: str = "none") -> List[Dict]:
        print(f"[MATCHER] Scraping Spotify: {url} (Browser: {cookies_from_browser})")
        tracks = []
        
        # 1. API APPROACH (Best quality metadata)
        if "/playlist/" in url or "/album/" in url:
            parts = url.split("?")[0].split("/")
            item_id = parts[-1]
            if self.api.check_login():
                if "/playlist/" in url:
                    tracks = self.api.get_playlist_tracks(item_id)
                elif "/album/" in url:
                    tracks = self.api.get_album_tracks(item_id)
                if tracks: return tracks

        # 2. BROWSER-AUTHENTICATED SCRAPE (Fallback for metadata)
        if cookies_from_browser != "none":
            try:
                import requests
                import tempfile
                import http.cookiejar
                
                print(f"[MATCHER] Attempting Spotify Browser Scrape for: {url}")
                cookie_path = tempfile.mktemp()
                # Use a non-DRM URL to extract cookies if possible
                ydl_opts = {'quiet': True, 'cookiesfrombrowser': (cookies_from_browser,), 'cookiefile': cookie_path}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    try: ydl.extract_info('https://www.spotify.com', download=False)
                    except: pass
                
                if not os.path.exists(cookie_path):
                    print("[MATCHER] Spotify Cookie export failed.")
                    return []

                cj = http.cookiejar.MozillaCookieJar(cookie_path)
                cj.load(ignore_discard=True, ignore_expires=True)
                session = requests.Session()
                session.cookies = cj
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                response = session.get(url, headers=headers, timeout=15)
                
                if os.path.exists(cookie_path): os.remove(cookie_path)
                
                if response.status_code == 200:
                    print(f"[MATCHER] Spotify Page Load Success ({len(response.text)} bytes)")
                    # Look for the JSON blob in the HTML
                    # Spotify Embeds metadata in several possible script tags
                    json_match = re.search(r'<script id="initial-state" type="text/plain">([^<]+)</script>', response.text)
                    if not json_match:
                         json_match = re.search(r'<script type="application/json" id="session">([^<]+)</script>', response.text)
                    
                    if json_match:
                        print("[MATCHER] Found Spotify JSON blob.")
                        import base64
                        data_str = json_match.group(1)
                        try:
                            # Try decoding if it looks like base64, otherwise load raw
                            try:
                                decoded = base64.b64decode(data_str).decode('utf-8')
                                data = json.loads(decoded)
                            except:
                                data = json.loads(data_str)
                        except Exception as je:
                            print(f"[MATCHER] Spotify JSON Parse Error: {je}")
                            return []
                        
                        # Deep search for tracks in the JSON
                        def find_spotify_tracks(obj):
                            found = []
                            if isinstance(obj, dict):
                                if 'type' in obj and obj['type'] == 'track' and 'name' in obj:
                                    artist = obj.get('artists', [{}])[0].get('name', 'Unknown')
                                    found.append({
                                        'artist': artist,
                                        'title': obj['name'],
                                        'album': obj.get('album', {}).get('name', ''),
                                        'duration': obj.get('duration_ms', 0) / 1000.0,
                                        'is_lossless': False,
                                        'is_playlist': True,
                                        'source': 'Spotify',
                                        'url': f"https://open.spotify.com/track/{obj.get('id')}"
                                    })
                                else:
                                    for v in obj.values(): found.extend(find_spotify_tracks(v))
                            elif isinstance(obj, list):
                                for item in obj: found.extend(find_spotify_tracks(item))
                            return found
                        
                        tracks = find_spotify_tracks(data)
                        if tracks:
                            # Deduplicate
                            seen = set()
                            unique = []
                            for t in tracks:
                                sig = f"{t['artist']}-{t['title']}"
                                if sig not in seen:
                                    seen.add(sig); unique.append(t)
                            print(f"[MATCHER] Spotify Browser Success: Found {len(unique)} tracks.")
                            return unique
                    
                    # ULTIMATE FALLBACK: Regex search for track links or names in HTML
                    print("[MATCHER] Spotify JSON search failed, attempting regex fallback...")
                    # Pattern for track names in titles or descriptions
                    # Often Spotify pages have "Track Name by Artist" in various meta tags
                    track_links = re.findall(r'https://open\.spotify\.com/track/([a-zA-Z0-9]+)', response.text)
                    if track_links:
                        print(f"[MATCHER] Found {len(set(track_links))} track links in HTML.")
                        for tid in list(set(track_links))[:50]:
                            tracks.append({
                                'artist': 'Spotify', 'title': f'Track {tid}',
                                'album': 'Spotify Playlist', 'is_lossless': False,
                                'is_playlist': True, 'source': 'Spotify',
                                'url': f"https://open.spotify.com/track/{tid}"
                            })
                        return tracks
            except Exception as e:
                print(f"[MATCHER] Spotify Browser Scrape Error: {e}")

        # 3. YT-DLP APPROACH (Final Fallback)
        try:
            ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': False}
            if cookies_from_browser.lower() != "none": ydl_opts['cookiesfrombrowser'] = (cookies_from_browser,)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                playlist_cover = info.get('thumbnail', '')
                entries = info.get('entries', [info])
                for entry in entries:
                    if not entry: continue
                    tracks.append({
                        'artist': entry.get('artist', entry.get('uploader', 'Unknown Artist')),
                        'title': entry.get('title', 'Unknown Title'),
                        'album': info.get('title', '') if 'entries' in info else entry.get('album', ''),
                        'is_lossless': False, 'is_playlist': 'entries' in info,
                        'source': 'Spotify',
                        'duration': entry.get('duration'),
                        'playlist_cover': playlist_cover
                    })
        except: pass
        return tracks

class SoundCloudCrateParser:
    def __init__(self):
        print("[MATCHER] SoundCloud Scraper Initialized.")

    def get_tracks(self, url: str, cookies_from_browser: str = "none") -> List[Dict]:
        print(f"[MATCHER] Scraping SoundCloud: {url} (Browser: {cookies_from_browser})")
        tracks = []
        try:
            ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': False}
            if cookies_from_browser.lower() != "none": ydl_opts['cookiesfrombrowser'] = (cookies_from_browser,)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                playlist_cover = info.get('thumbnail', '')
                # Check of het een set is (entries)
                entries = info.get('entries', [info])
                for entry in entries:
                    if not entry: continue
                    tracks.append({
                        'artist': entry.get('uploader', entry.get('artist', 'Unknown Artist')),
                        'title': entry.get('title', 'Unknown Title'),
                        'album': info.get('title', 'SoundCloud Set') if 'entries' in info else entry.get('album', 'SoundCloud'),
                        'is_lossless': False,
                        'is_playlist': 'entries' in info,
                        'duration': entry.get('duration'),
                        'url': entry.get('url', entry.get('webpage_url', url)),
                        'source': 'SoundCloud',
                        'playlist_cover': playlist_cover
                    })
        except Exception as e:
            print(f"[MATCHER] SoundCloud Scraper Error: {e}")
        return tracks

class BandcampCrateParser:
    def __init__(self, api_handler=None):
        print("[MATCHER] Bandcamp Scraper Initialized.")
        from bandcamp_api_handler import BandcampApiHandler
        self.api = api_handler or BandcampApiHandler()

    def get_tracks(self, url: str, cookies_from_browser: str = "none") -> List[Dict]:
        print(f"[MATCHER] Scraping Bandcamp: {url} (Browser: {cookies_from_browser})")
        tracks = []
        
        # 1. PROFILE/COLLECTION APPROACH
        if "bandcamp.com/" in url and not any(x in url for x in [".bandcamp.com", "/album/", "/track/"]):
             username = url.split("bandcamp.com/")[-1].strip("/")
             if username:
                  print(f"[MATCHER] Attempting Bandcamp Collection Scraping for: {username}")
                  # Try API first
                  if self.api.login(username):
                       tracks = self.api.get_collection_tracks()
                       if tracks:
                            for t in tracks: t['source'] = 'Bandcamp'
                            return tracks
                  
                  # HTML Fallback if API fails or returns nothing
                  try:
                       import requests
                       headers = {'User-Agent': 'Mozilla/5.0'}
                       response = requests.get(url, headers=headers, timeout=10)
                       if response.status_code == 200:
                            # We zoeken naar album links in de collection, we filteren &quot; en andere rommel
                            raw_links = re.findall(r'https://[^\"? \n]+\.bandcamp\.com/album/[^\"? \n]+', response.text)
                            album_links = []
                            for link in raw_links:
                                 clean_link = link.split('&quot;')[0].split('\\')[0].strip()
                                 if clean_link not in album_links:
                                      album_links.append(clean_link)
                            
                            if album_links:
                                 print(f"[MATCHER] Found {len(album_links)} unique albums in collection HTML.")
                                 # We pingen de eerste 15 albums om de UI responsief te houden
                                 for album_url in album_links[:15]:
                                      tracks.extend(self.get_tracks(album_url, cookies_from_browser))
                                 return tracks
                  except Exception as e:
                       print(f"[MATCHER] HTML Fallback Error: {e}")

        # 2. YT-DLP FALLBACK (Albums/Tracks)
        try:
            ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': False}
            if cookies_from_browser.lower() != "none": ydl_opts['cookiesfrombrowser'] = (cookies_from_browser,)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                playlist_cover = info.get('thumbnail', '')
                entries = info.get('entries', [info])
                for entry in entries:
                    if not entry: continue
                    tracks.append({
                        'artist': entry.get('artist', entry.get('uploader', 'Unknown Artist')),
                        'title': entry.get('title', 'Unknown Title'),
                        'album': info.get('title', 'Bandcamp Release') if 'entries' in info else entry.get('album', 'Bandcamp'),
                        'is_lossless': True, 'is_playlist': 'entries' in info,
                        'duration': entry.get('duration'),
                        'source': 'Bandcamp',
                        'playlist_cover': playlist_cover
                    })
        except: pass
        return tracks

class BeatportCrateParser:
    def __init__(self):
        print("[MATCHER] Beatport Scraper Initialized.")

    def get_tracks(self, url: str, cookies_from_browser: str = "none") -> List[Dict]:
        print(f"[MATCHER] Scraping Beatport: {url}")
        tracks = []
        
        # 1. BROWSER-AUTHENTICATED APPROACH (For /library or Collection)
        if "/library" in url or "/collection/" in url:
            if cookies_from_browser != "none":
                try:
                    import requests
                    import tempfile
                    import http.cookiejar
                    
                    cookie_path = tempfile.mktemp()
                    ydl_opts = {'quiet': True, 'cookiesfrombrowser': (cookies_from_browser,), 'cookiefile': cookie_path}
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        try: ydl.extract_info('https://www.beatport.com', download=False)
                        except: pass
                    
                    cj = http.cookiejar.MozillaCookieJar(cookie_path)
                    cj.load(ignore_discard=True, ignore_expires=True)
                    session = requests.Session()
                    session.cookies = cj
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                    response = session.get(url, headers=headers, timeout=15)
                    
                    if os.path.exists(cookie_path): os.remove(cookie_path)
                    
                    if response.status_code == 200:
                        json_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">([^<]+)</script>', response.text)
                        if json_match:
                            data = json.loads(json_match.group(1))
                            props = data.get('props', {}).get('pageProps', {})
                            
                            # Deep search for track results
                            def find_tracks_recursive(obj, depth=0):
                                found = []
                                if depth > 30: return found
                                if isinstance(obj, dict):
                                    # Beatport library results often live in 'results' key
                                    if 'results' in obj and isinstance(obj['results'], list) and len(obj['results']) > 0:
                                        first = obj['results'][0]
                                        # Very broad check for track-like objects
                                        if isinstance(first, dict) and ('artists' in first or 'artist' in first) and ('name' in first or 'title' in first):
                                            print(f"[MATCHER] Found Beatport results list (len: {len(obj['results'])}) at depth {depth}")
                                            for item in obj['results']:
                                                artist = item.get('artists', [{}])[0].get('name', item.get('artist', {}).get('name', 'Unknown'))
                                                title = item.get('name') or item.get('title', 'Unknown')
                                                
                                                release = item.get('release', {})
                                                album = release.get('name') if isinstance(release, dict) else ""
                                                
                                                dur = 0
                                                if isinstance(item.get('duration'), dict):
                                                    dur = item['duration'].get('milliseconds', 0) / 1000.0
                                                else:
                                                    dur = item.get('duration', 0)

                                                found.append({
                                                    'artist': artist,
                                                    'title': title,
                                                    'album': album,
                                                    'duration': dur,
                                                    'bpm': item.get('bpm', 0),
                                                    'key': item.get('key', {}).get('name', '') if isinstance(item.get('key'), dict) else str(item.get('key', '')),
                                                    'is_lossless': True,
                                                    'is_playlist': True,
                                                    'source': 'Beatport',
                                                    'url': f"https://www.beatport.com/track/{item.get('slug', 'track')}/{item.get('id', '')}"
                                                })
                                            return found
                                    for v in obj.values():
                                        res = find_tracks_recursive(v, depth + 1)
                                        if res: found.extend(res)
                                elif isinstance(obj, list):
                                    for item in obj:
                                        res = find_tracks_recursive(item, depth + 1)
                                        if res: found.extend(res)
                                return found
                            
                            tracks = find_tracks_recursive(props)
                            
                            if not tracks:
                                # ULTIMATE FALLBACK: Regex search for track titles in HTML
                                print("[MATCHER] JSON search failed, attempting regex fallback...")
                                track_matches = re.findall(r'\"artist\":\{\"name\":\"([^\"]+)\"\},\"name\":\"([^\"]+)\"', response.text)
                                for a, t in track_matches:
                                    tracks.append({
                                        'artist': a, 'title': t, 'album': 'Beatport Library',
                                        'is_lossless': True, 'is_playlist': True, 'source': 'Beatport'
                                    })
                            
                            if tracks:
                                # Deduplicate
                                unique = []
                                seen = set()
                                for t in tracks:
                                    sig = f"{t['artist']}-{t['title']}"
                                    if sig not in seen:
                                        seen.add(sig); unique.append(t)
                                print(f"[MATCHER] Beatport Success: Found {len(unique)} tracks.")
                                return unique
                            if tracks:
                                print(f"[MATCHER] Beatport JSON Success: Found {len(tracks)} tracks.")
                                return tracks
                except Exception as e:
                    print(f"[MATCHER] Beatport Auth Scrape Error: {e}")

        # 2. YT-DLP FALLBACK (Normal tracks/charts)
        try:
            ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': False}
            if cookies_from_browser.lower() != "none": ydl_opts['cookiesfrombrowser'] = (cookies_from_browser,)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                entries = info.get('entries', [info])
                for entry in entries:
                    if not entry: continue
                    tracks.append({
                        'artist': entry.get('artist', 'Unknown Artist'),
                        'title': entry.get('title', 'Unknown Title'),
                        'album': info.get('title', '') if 'entries' in info else entry.get('album', ''),
                        'is_lossless': True, # Beatport is a pro source
                        'is_playlist': 'entries' in info,
                        'duration': entry.get('duration'),
                        'source': 'Beatport',
                        'playlist_cover': info.get('thumbnail', '')
                    })
        except: pass
        return tracks

class UniversalMatcher:
    def __init__(self, spotify_api=None, tidal_api=None, bandcamp_api=None):
        self.spotify = SpotifyCrateParser(api_handler=spotify_api)
        self.tidal = TidalCrateParser(api_handler=tidal_api)
        self.soundcloud = SoundCloudCrateParser()
        self.bandcamp = BandcampCrateParser(api_handler=bandcamp_api)
        self.beatport = BeatportCrateParser()
        
    def _resolve_soundcloud_you(self, url: str, cookies_from_browser: str = "none") -> str:
        """Resolves browser-only SoundCloud /you/ aliases to actual username URLs."""
        if "soundcloud.com/you" not in url or cookies_from_browser == "none":
            return url
            
        print(f"[MATCHER] Auto-resolving SoundCloud 'you' alias via {cookies_from_browser}...")
        try:
            import requests
            # We pingen de URL met yt-dlp om de uiteindelijke URL te krijgen (redirects)
            ydl_opts = {'quiet': True, 'cookiesfrombrowser': (cookies_from_browser,), 'noplaylist': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # We trekken metadata van de 'you' pagina, yt-dlp volgt redirects
                info = ydl.extract_info("https://soundcloud.com/you", download=False)
                if info and 'webpage_url' in info:
                    final_url = info['webpage_url']
                    if "soundcloud.com/you" not in final_url:
                        resolved = url.replace("soundcloud.com/you", final_url.replace("https://", "").replace("http://", ""))
                        print(f"[MATCHER] Successfully resolved to: {resolved}")
                        return resolved
        except Exception as e:
            print(f"[MATCHER] Resolve failed: {e}")
        return url

    def _parse_raw_text(self, text: str) -> List[Dict]:
        """YOLO Mode: Extracts tracks from raw copy-pasted text from a browser."""
        print("[MATCHER] YOLO Mode: Parsing raw text block...")
        tracks = []
        # Split op verschillende newline varianten
        lines = re.split(r'\r\n|\r|\n', text)
        
        # FILTER: Agressieve ruis-onderdrukking voor logs, terminal prompts en code
        noise_patterns = [
            r'Traceback \(most recent call last\)',
            r'File ".*", line \d+',
            r'IndentationError:',
            r'\[flark@.*\]\$',
            r'^http', 
            r'^[ \t]*[\|✓-]',
            r'^▀+$', r'^▄+$',
            r'^\[(SYSTEM|MATCHER|TIDAL|SPOTIFY|SOUNDCLOUD|BANDCAMP|XML|DEBUG|INFO|ERROR|WARN|FATAL)\]',
            r'got an unexpected keyword argument',
            r'Unsupported URL:',
            r'Shutting down DJwerk',
            r'Awaiting URL Input',
            r'self\.', r'def ', r'import ', r'class ', r'elif ', r'return ', r'if ', r'else:', r'finally:', r'except ',
            r'\{.*\}', r'\(.*\)', r'\[.*\]', # Code-achtige haken
            r'^\d+\s*[-+]' # Diff lines
        ]

        def is_likely_track(artist, title):
            # Check of het niet toevallig code of logs zijn
            invalid_keywords = ['self', 'def', 'import', 'class', 'print', 'return', 'if', 'else', 'elif', 'finally', 'except', 'tracks', 'track_data', 'result', 'success']
            a_lower = artist.lower()
            t_lower = title.lower()
            
            # Geen lege waarden of extreem korte waarden
            if len(artist) < 2 or len(title) < 2: return False
            # Geen python code fragmenten
            if any(word in a_lower.split() for word in invalid_keywords): return False
            if any(word in t_lower.split() for word in invalid_keywords): return False
            # Geen terminal prompts of logs in de artist/title
            if ">>" in artist or ">>" in title: return False
            # Geen pure getallen
            if artist.isdigit() or title.isdigit(): return False
            
            return True
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line or len(line) < 3: continue
            
            if any(re.search(p, line, re.IGNORECASE) for p in noise_patterns): continue
            if len(line) > 150: continue
            
            # Verwijder tracknummers "1. Artist - Title" of "01 Artist - Title"
            line = re.sub(r'^\d+[\s\.\)-]+', '', line)
            
            # Patroon: "Artist - Title" (meest voorkomend)
            if " - " in line:
                parts = line.split(" - ", 1)
                a, t = parts[0].strip(), parts[1].strip()
                if is_likely_track(a, t):
                    tracks.append({
                        'artist': a, 'title': t,
                        'album': '', 'is_lossless': False, 'is_playlist': True,
                        'source': 'TEXT'
                    })
            # Patroon: "Artist : Title" of "Artist | Title"
            elif " : " in line or " | " in line:
                sep = " : " if " : " in line else " | "
                parts = line.split(sep, 1)
                a, t = parts[0].strip(), parts[1].strip()
                if is_likely_track(a, t):
                    tracks.append({
                        'artist': a, 'title': t,
                        'album': '', 'is_lossless': False, 'is_playlist': True,
                        'source': 'TEXT'
                    })
            # Fallback: Tidal/Spotify copy-paste waar de volgende regel de artiest is
            # Alleen als de huidige regel niet op code lijkt
            elif i + 1 < len(lines):
                next_line = lines[i+1].strip()
                if len(line) > 2 and len(next_line) > 2 and not line.isdigit() and "http" not in line:
                    if is_likely_track(next_line, line) and not any(re.search(p, next_line, re.IGNORECASE) for p in noise_patterns):
                        tracks.append({
                            'artist': next_line,
                            'title': line,
                            'album': '', 'is_lossless': False, 'is_playlist': True,
                            'source': 'TEXT'
                        })
        
        # Deduplicatie voor de ruwe parse
        unique_tracks = []
        seen = set()
        for t in tracks:
            sig = f"{t['artist'].lower()}-{t['title'].lower()}"
            if sig not in seen and "http" not in t['title']:
                seen.add(sig)
                unique_tracks.append(t)
                
        print(f"[MATCHER] YOLO Parser vond potentieel {len(unique_tracks)} tracks na filtering.")
        return unique_tracks

    def get_tracks(self, url: str, cookies_from_browser: str = "none") -> List[Dict]:
        """Routes the URL or raw text to the correct scraper."""
        # Is het een blok tekst in plaats van een URL?
        if len(url.split('\n')) > 1 or not url.startswith("http"):
            return self._parse_raw_text(url)

        # Smart Alias Resolution for SoundCloud /you/
        if "soundcloud.com/you" in url:
            url = self._resolve_soundcloud_you(url, cookies_from_browser)

        if "spotify.com" in url: return self.spotify.get_tracks(url, cookies_from_browser)
        if "tidal.com" in url: return self.tidal.get_tracks(url, cookies_from_browser)
        if "soundcloud.com" in url: return self.soundcloud.get_tracks(url, cookies_from_browser)
        if "bandcamp.com" in url: return self.bandcamp.get_tracks(url, cookies_from_browser)
        if "beatport.com" in url: return self.beatport.get_tracks(url, cookies_from_browser)

        return [{"artist": "Search", "title": url, "is_playlist": False, "is_lossless": False, "source": "Search"}]
        
