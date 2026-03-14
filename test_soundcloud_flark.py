import os
from djwerk_matcher import SoundCloudCrateParser

def test_soundcloud_personal_set():
    url = "https://soundcloud.com/flark/sets/drum-bass"
    sc = SoundCloudCrateParser()
    
    print(f"\n[TESTING] SOUNDCLOUD PERSONAL SET - {url}")
    print(f"  > Attempting to resolve via Firefox session...")
    
    try:
        # We gebruiken de firefox cookies uit je settings
        tracks = sc.get_tracks(url, cookies_from_browser="firefox")
        
        if tracks:
            print(f"  [SUCCESS] Found {len(tracks)} tracks in your 'Drum & Bass' set!")
            for i, t in enumerate(tracks[:10]):
                artist = t.get('artist', 'Unknown')
                title = t.get('title', 'Unknown')
                print(f"    {i+1:02d}. {artist} - {title}")
            return True
        else:
            print(f"  [FAILED] No tracks found. Scraper returned empty list.")
            return False
            
    except Exception as e:
        print(f"  [ERROR] Scraper failed: {e}")
        return False

if __name__ == "__main__":
    test_soundcloud_personal_set()
