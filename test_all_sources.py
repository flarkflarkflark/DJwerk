import os
import time
from djwerk_matcher import UniversalMatcher
from djwerk_core import DJwerkCore

def test_source_sync(source_name, url, format_choice="flac", use_cookies=False):
    print(f"\n[TESTING] {source_name.upper()} ({format_choice.upper()}) - {url}")
    matcher = UniversalMatcher()
    core = DJwerkCore(download_path="test_downloads")
    
    cookies = "firefox" if use_cookies else "none"
    
    # 1. MATCHING
    print(f"  > Matching tracks (Cookies: {cookies})...")
    try:
        tracks = matcher.get_tracks(url, cookies_from_browser=cookies)
    except Exception as e:
        print(f"  [ERROR] Matcher crashed: {e}")
        return False

    if not tracks:
        print(f"  [FAILED] No tracks found for {source_name}")
        return False
    
    print(f"  [SUCCESS] Found {len(tracks)} tracks. Testing first one...")
    track_data = tracks[0]
    
    # 2. SYNCING (Download + Meta)
    target_format = "flac" if "flac" in format_choice.lower() else "mp3"
    print(f"  > Syncing: {track_data.get('artist', 'Unknown')} - {track_data.get('title', 'Unknown')}")
    
    crate_name = f"Test_{source_name}_{target_format}"
    
    # Nabootsen van djwerk_controller.py logica:
    # Als er geen specifieke track url is, OF het is een bron die yt-dlp niet kan direct downloaden, fallback naar ytsearch
    track_url = track_data.get('url')
    if not track_url or 'spotify' in track_url or 'tidal' in track_url:
        track_url = f"ytsearch:{track_data.get('artist', '')} {track_data.get('title', '')}"

    success, result, s_info = core.download_track(
        track_url, 
        target_format, 
        None, 
        cookies, 
        crate_name, 
        1, 
        artist=track_data.get('artist'), 
        source=track_data.get('source', source_name)
    )
    
    if success and os.path.exists(result):
        print(f"  [SUCCESS] Downloaded to: {result}")
        meta_success = core.update_metadata(
            result, track_data.get('artist', 'Unknown'), track_data.get('title', 'Unknown'), 
            track_data.get('album'), track_data.get('bpm'), 
            track_data.get('key')
        )
        if meta_success:
            print(f"  [SUCCESS] Metadata injected.")
            return True
        else:
            print(f"  [WARN] Metadata injection failed, but download succeeded.")
            return True
    else:
        print(f"  [FAILED] Download failed: {result}")
        return False

if __name__ == "__main__":
    tests = [
        # SOUNDCLOUD: Valid track URL
        ("SoundCloud (Track)", "https://soundcloud.com/eatbrain/mythic-image-mental-echo-eatbrain-172", "flac", True),
        
        # BANDCAMP: Full Album
        ("Bandcamp (Album)", "https://steveroach.bandcamp.com/album/tomorrow", "flac", False),
        
        # TIDAL: Playlist (we mock a successful api response by passing a track directly to YOLO format)
        ("Tidal via YOLO", "Noisia - Dead Limit\nSyran - Crazy Fruits", "flac", False),
        
        # SPOTIFY via YOLO
        ("Spotify via YOLO", "The Chemical Brothers - Block Rockin' Beats", "mp3", False)
    ]

    results = []
    if not os.path.exists("test_downloads"):
        os.makedirs("test_downloads")

    for name, url, fmt, cookies in tests:
        try:
            res = test_source_sync(name, url, fmt, use_cookies=cookies)
            results.append((name, fmt, "PASS" if res else "FAIL"))
        except Exception as e:
            print(f"  [CRASH] {e}")
            results.append((name, fmt, f"CRASH: {e}"))

    print("\n" + "="*50)
    print("           ULTIMATE SYNC REPORT")
    print("="*50)
    for name, fmt, res in results:
        status_icon = "✓" if res == "PASS" else "✗"
        print(f"{status_icon} {name:<20} [{fmt.upper():<5}] -> {res}")
    print("="*50)
