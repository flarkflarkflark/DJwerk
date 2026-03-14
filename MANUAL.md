# The Ultimate DJwerk Manual 🎧

Welcome to **DJwerk**, the universal crate engine by flarkAUDIO that bridges the gap between liquid cloud music and solid physical DJ libraries.

## What is DJwerk?
DJwerk is an autonomous tool designed for DJs who want to sync their libraries across different platforms. It downloads tracks with the highest possible quality (FLAC or MP3 320kbps), embeds rich metadata and cover art, and updates your DJ software databases directly.

## Using Universal Sync & YOLO Mode
1. **URL Sync:** Copy a URL from Tidal, Spotify, SoundCloud, Bandcamp, or Beatport and paste it into the main entry.
2. **YOLO Mode:** Copy a raw block of text (like a tracklist from a website) and click **PASTE & SYNC CRATE**. DJwerk will intelligently filter out the noise and find the best matches.
3. **Selector:** In the **Crate Selector** window, you can filter tracks, see their duration, and choose your preferred output format.
4. **Processing:** DJwerk will sync the tracks, embed BPM/Key/Art, and apply your chosen normalization.

## The Export Center
Once your tracks are synced, use the **Export Center** to push them into your DJ software:

### 1. Pioneer Rekordbox
DJwerk generates a `library.xml` file.
- In Rekordbox, go to **Preferences** -> **View** and enable **rekordbox xml**.
- Point the XML location to the `library.xml` in your DJwerk folder.
- Your crates will appear in the "rekordbox xml" section of the sidebar.

### 2. Denon / Engine DJ
DJwerk can inject tracks directly into the `m.db` database.
- Connect your Engine DJ device (USB or HDD).
- Use the Export Center to push tracks to the database on your drive.
- Tracks appear instantly on your hardware (Prime Go, SC6000, etc.) without a re-scan.

### 3. Mixxx (Open Source)
DJwerk detects your Mixxx database (Standard or Flatpak) and injects tracks directly.
- Ensure Mixxx is closed during the export.
- Push the tracks via the Export Center.
- Open Mixxx and your new tracks will be ready in the library.

### 4. Algoriddim djay Pro / Serato
DJwerk generates "Rich M3U8" playlists.
- Drag the `_RICH.m3u8` file from your crate folder into djay Pro or Serato.
- All metadata, including duration and tags, will be imported immediately.

## Pro Features

### Smart Gain Control
In **Settings -> General**, you can enable normalization. 
- **LUFS:** Adjust the perceived loudness (Standard is -14.0).
- **Peak:** Ensure no clipping by setting a Safety Peak (e.g., -1.0 dB).
- **Interactive:** Scroll your mouse wheel over the value to adjust it in logical steps.

### Universal Browser Authentication
In **Settings -> Connections**, select your primary browser (e.g., Firefox). 
- DJwerk will use your active browser session to bypass captchas and access your private playlists on SoundCloud and Spotify.
- Look for the **CONNECTED** status to verify your session is active.

---
*Liquid to Solid | flarkAUDIO 2026*
