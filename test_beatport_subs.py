
import requests
import yt_dlp
import http.cookiejar
import tempfile
import os
import re
import json
from djwerk_matcher import UniversalMatcher

def test_beatport_subscriptions(browser="firefox"):
    print(f"Testing Beatport Subscriptions with cookies from {browser}...")
    matcher = UniversalMatcher()
    url = "https://www.beatport.com/subscriptions"
    
    tracks = matcher.get_tracks(url, cookies_from_browser=browser)
    if tracks:
        print(f"   ✓ SUCCESS: Found {len(tracks)} tracks on subscriptions page (unexpected but cool).")
    else:
        print(f"   ✗ INFO: No tracks found on subscriptions page. (Likely just a landing page).")

if __name__ == "__main__":
    test_beatport_subscriptions()
