from djwerk_matcher import UniversalMatcher

def test_platform_direct():
    matcher = UniversalMatcher()
    
    # Direct URLs to verify current platform support
    test_cases = [
        ("Tidal", "https://tidal.com/browse/track/256729226"),
        ("Spotify", "https://open.spotify.com/playlist/37i9dQZF1DX6J5vU4Y6o1P"),
        ("Bandcamp", "https://finalgasp.bandcamp.com/album/new-day-symptoms"),
        ("SoundCloud", "https://soundcloud.com/eatbrain/sets/eatbrain-172-mythic-image-chimeric")
    ]
    
    results = []
    
    print("\n[VALIDATING PLATFORM LINKS]")
    for name, url in test_cases:
        print(f"  [TESTING] {name}: {url}")
        try:
            tracks = matcher.get_tracks(url)
            if tracks:
                print(f"    ✓ SUCCESS: Found {len(tracks)} tracks.")
                results.append((name, url, f"SUCCESS ({len(tracks)} tracks)"))
            else:
                print(f"    ✗ FAILED: No tracks found.")
                results.append((name, url, "FAILED"))
        except Exception as e:
            print(f"    ! ERROR: {e}")
            results.append((name, url, f"ERROR: {e}"))

    print("\n" + "="*80)
    print("           FINAL PLATFORM LINK VALIDATION REPORT")
    print("="*80)
    for name, url, res in results:
        print(f"{name:<12} | {res:<20} | {url}")
    print("="*80)

if __name__ == "__main__":
    test_platform_direct()
