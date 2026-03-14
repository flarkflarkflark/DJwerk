import requests
import re
from djwerk_matcher import UniversalMatcher

def extract_links(url, pattern):
    print(f"\n[SCRAPING] {url} ...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            links = re.findall(pattern, response.text)
            # Clean and deduplicate
            unique_links = []
            for l in links:
                if isinstance(l, tuple): l = l[0]
                l = l.strip().replace('\\', '')
                if l not in unique_links:
                    unique_links.append(l)
            print(f"  > Found {len(unique_links)} potential links.")
            return unique_links
    except Exception as e:
        print(f"  [ERROR] Scraping failed: {e}")
    return []

def test_homepage_links():
    matcher = UniversalMatcher()
    
    # Homepage configs: (Name, URL, Regex Pattern)
    configs = [
        ("Tidal", "https://tidal.com", r'https://tidal\.com/browse/(?:track|album|playlist|mix)/[a-zA-Z0-9-]+'),
        ("Spotify", "https://open.spotify.com", r'https://open\.spotify\.com/(?:track|album|playlist)/[a-zA-Z0-9]+'),
        ("Bandcamp", "https://bandcamp.com", r'https://[a-zA-Z0-9-]+\.bandcamp\.com/(?:track|album)/[a-zA-Z0-9-]+'),
        ("SoundCloud", "https://soundcloud.com", r'https://soundcloud\.com/[a-zA-Z0-9-]+/[a-zA-Z0-9-]+')
    ]
    
    results = []
    
    for name, url, pattern in configs:
        links = extract_links(url, pattern)
        # Test up to 3 links per homepage
        test_links = links[:3]
        if not test_links:
            results.append((name, "No links found on homepage"))
            continue
            
        for test_link in test_links:
            print(f"  [TESTING] {test_link}")
            try:
                tracks = matcher.get_tracks(test_link)
                if tracks:
                    print(f"    ✓ SUCCESS: Found {len(tracks)} tracks.")
                    results.append((name, f"✓ {test_link} -> {len(tracks)} tracks"))
                else:
                    print(f"    ✗ FAILED: No tracks extracted.")
                    results.append((name, f"✗ {test_link} -> FAIL"))
            except Exception as e:
                print(f"    ! CRASH: {e}")
                results.append((name, f"! {test_link} -> CRASH"))

    print("\n" + "="*60)
    print("           HOMEPAGE LINK VALIDATION REPORT")
    print("="*60)
    for name, res in results:
        print(f"{name:<12} : {res}")
    print("="*60)

if __name__ == "__main__":
    test_homepage_links()
