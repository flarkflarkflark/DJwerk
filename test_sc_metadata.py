import yt_dlp
import json
import time

url = 'https://soundcloud.com/flark/sets/remixes'
ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': False}

start = time.time()
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(url, download=False)
    entries = info.get('entries', [])
    print(f"Fetch took {time.time() - start:.2f} seconds.")
    print(f"Entries count: {len(entries)}")
    for i, entry in enumerate(entries):
        print(f"Entry {i}: Title={entry.get('title')} | Uploader={entry.get('uploader')}")
