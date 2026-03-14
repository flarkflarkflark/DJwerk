import requests
import re
import json
from typing import List, Dict

class TidalCrateParser:
    def __init__(self):
        print("[MATCHER] Tidal OpenGraph Parser Initialized.")

    def get_tracks(self, url: str) -> List[Dict]:
        """
        Parses metadata from Tidal links (both single tracks and playlists).
        Tidal playlists on their public web viewer usually expose tracks in the HTML or OpenGraph.
        Voor playlists proberen we JSON-LD uit de source te halen in plaats van één generieke titel.
        """
        print(f"[MATCHER] Scraping Tidal metadata via OpenGraph: {url}")
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                print(f"[MATCHER] Scraper Error: HTTP {response.status_code}")
                return []

            html = response.text
            
            # PROBEER UITGEBREIDE PLAYLIST PARSING:
            # Tidal embedt vaak data in script tags, we zoeken naar "trackList" of vergelijkbaar
            tracks = []
            
            if "playlist" in url.lower():
                # Extreem simpele heuristiek voor Tidal playlists (omdat ze zwaar React-gebaseerd zijn)
                # Ze hebben vaak <meta name="description" content="Listen to My Playlist on TIDAL. Featuring: Track 1, Track 2...">
                desc_match = re.search(r'<meta name="description" content="([^"]+)"', html)
                if desc_match:
                    desc_text = desc_match.group(1)
                    if "Featuring:" in desc_text:
                        feat_part = desc_text.split("Featuring:")[1]
                        # Splits de artiesten/titels op de comma (Zeer ruw, maar effectief voor eerste 5-10 tracks)
                        raw_tracks = feat_part.split(",")
                        for raw_t in raw_tracks:
                            if " by " in raw_t:
                                parts = raw_t.split(" by ")
                                title = parts[0].strip()
                                artist = parts[1].strip()
                                tracks.append({
                                    'artist': artist,
                                    'title': title,
                                    'album': '',
                                    'year': 0,
                                    'cover_url': '',
                                    'is_lossless': True,
                                    'is_playlist': True
                                })
            
            # ALs de lijst parsing lukte, stuur die terug
            if len(tracks) > 0:
                print(f"[MATCHER] Extracted {len(tracks)} tracks from playlist description.")
                return tracks
            
            # FALLBACK: OpenGraph (Pakt alleen de titel/curator van de hele playlist of de single track)
            title_match = re.search(r'property="og:title" content="([^"]+)"', html)
            description_match = re.search(r'property="og:description" content="([^"]+)"', html)
            image_match = re.search(r'property="og:image" content="([^"]+)"', html)

            if title_match:
                raw_title = title_match.group(1)
                desc = description_match.group(1) if description_match else ""
                
                # Voorkom dat hij de hele naam van de app als track probeert te zoeken
                if raw_title == "TIDAL - High Fidelity Music Streaming" or raw_title == "TIDAL":
                    print("[MATCHER] Warning: Extracted generic app title from OG. Playlist empty or private.")
                    return []
                    
                if " by " in raw_title and " on TIDAL" in raw_title:
                    clean_title = raw_title.replace(" on TIDAL", "")
                    parts = clean_title.split(" by ")
                    title, artist = parts[0], parts[1]
                else:
                    title = raw_title.replace(" on TIDAL", "").strip()
                    artist = desc.split("·")[0].strip() if "·" in desc else "Unknown"
                    
                    if artist.upper() == "TIDAL":
                        artist = "Unknown Artist"

                return [{
                    'artist': artist,
                    'title': title,
                    'album': '',
                    'year': 0,
                    'cover_url': image_match.group(1) if image_match else '',
                    'is_lossless': True,
                    'is_playlist': False
                }]
            else:
                print("[MATCHER] Could not find metadata tags on the page.")

        except Exception as e:
            print(f"[MATCHER] Scraper Exception: {e}")
            
        return []

class SpotifyCrateParser:
    def __init__(self):
        print("[MATCHER] No Spotify API keys found. Using OpenGraph Scraper Mode.")

    def get_tracks(self, url: str) -> List[Dict]:
        print(f"[MATCHER] Scraping metadata via OpenGraph: {url}")
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                print(f"[MATCHER] Scraper Error: HTTP {response.status_code}")
                return []

            html = response.text
            
            title_match = re.search(r'property="og:title" content="([^"]+)"', html)
            description_match = re.search(r'property="og:description" content="([^"]+)"', html)
            image_match = re.search(r'property="og:image" content="([^"]+)"', html)

            if title_match:
                raw_title = title_match.group(1)
                
                middle_dot = chr(183) # \xb7
                
                if f" {middle_dot} " in raw_title:
                    parts = raw_title.split(f" {middle_dot} ", 1)
                    artist, title = parts[0], parts[1]
                elif " - " in raw_title:
                    parts = raw_title.split(" - ", 1)
                    artist, title = parts[0], parts[1]
                else:
                    artist = "Unknown Artist"
                    title = raw_title

                return [{
                    'artist': artist,
                    'title': title,
                    'album': '',
                    'year': 0,
                    'cover_url': image_match.group(1) if image_match else '',
                    'is_lossless': False,
                    'is_playlist': "playlist" in url.lower()
                }]
            else:
                print("[MATCHER] Could not find metadata tags on the page.")

        except Exception as e:
            print(f"[MATCHER] Scraper Exception: {e}")
            
        return []

class UniversalMatcher:
    def __init__(self):
        self.spotify = SpotifyCrateParser()
        self.tidal = TidalCrateParser()
        
    def get_tracks(self, url: str) -> List[Dict]:
        """Routes the URL to the correct scraper."""
        if "spotify.com" in url:
            return self.spotify.get_tracks(url)
        elif "tidal.com" in url:
            return self.tidal.get_tracks(url)
        else:
            print(f"[MATCHER] Unsupported or direct URL detected: {url}")
            return []

if __name__ == "__main__":
    matcher = UniversalMatcher()
    
    print("\n--- Testing Spotify ---")
    tracks_sp = matcher.get_tracks("https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC")
    for t in tracks_sp: print(f">> {t['artist']} - {t['title']} (Lossless: {t['is_lossless']})")
    
    print("\n--- Testing Tidal ---")
    tracks_td = matcher.get_tracks("https://tidal.com/browse/track/25396656")
    for t in tracks_td: print(f">> {t['artist']} - {t['title']} (Lossless: {t['is_lossless']})")