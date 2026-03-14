
import sys
import os
# Voeg huidige map toe aan path voor imports
sys.path.append(os.getcwd())

from djwerk_matcher import TidalCrateParser
from tidal_api_handler import TidalApiHandler

url = "https://tidal.com/playlist/2e79fb59-b677-459e-9bd4-6c75e93e3287"
parser = TidalCrateParser()

print(f"Testing URL: {url}")
tracks = parser.get_tracks(url)
print(f"Found {len(tracks)} tracks.")
if tracks:
    print(f"First track: {tracks[0]}")
else:
    print("No tracks found or error occurred.")
