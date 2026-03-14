import os
from djwerk_matcher import UniversalMatcher

def test_soundcloud_private():
    url = "https://soundcloud.com/you/sets"
    matcher = UniversalMatcher()
    
    print(f"\n[TESTING] SOUNDCLOUD PRIVATE SYNC - {url}")
    print(f"  > Attempting to resolve via Firefox session...")
    
    try:
        # We gebruiken de firefox cookies uit je settings
        from djwerk_matcher import SoundCloudCrateParser
        sc = SoundCloudCrateParser()
        tracks = sc.get_tracks(url, cookies_from_browser="firefox")
        
        if tracks:
            print(f"  [SUCCESS] Found {len(tracks)} tracks in your private sets!")
            for i, t in enumerate(tracks[:5]):
                artist = t.get('artist', 'Unknown')
                title = t.get('title', 'Unknown')
                print(f"    {i+1}. {artist} - {title}")
            return True
        else:
            print(f"  [FAILED] No tracks found. This URL ('/you/') is a browser-only alias.")
            print(f"  [TIP] Try using your direct profile URL instead: https://soundcloud.com/[your-username]/sets")
            return False
            
    except Exception as e:
        print(f"  [ERROR] Scraper failed: {e}")
        return False

if __name__ == "__main__":
    test_soundcloud_private()
