# DJwerk 🎧

**DJwerk** is the universal "Physical Crate Engine" of the flarkAUDIO suite. It transforms volatile cloud playlists into a robust, physical, and platform-independent music collection for the professional DJ.

## The Goal: Offline Reliability for DJs
DJs should no longer be dependent on Wi-Fi or streaming subscriptions during a set. DJwerk pulls music from the cloud and converts it into physical files (FLAC/MP3) with universal metadata that works across all hardware and software.

## Key Features (v0.2.0)

### 1. Universal Input & YOLO Mode 🚀
- **Native Support:** Sync tracks, albums, and playlists from **Tidal**, **Spotify**, **SoundCloud**, **Bandcamp**, and **Beatport**.
- **YOLO Mode:** Paste any raw text (tracklists, browser snippets) and DJwerk will intelligently match and sync the tracks from open sources.
- **Universal Browser Auth:** Uses your active browser session (Chrome, Firefox, etc.) to bypass DRM, captchas, and private access restrictions.

### 2. Pro-Grade Processing 🎚️
- **Smart Normalization:** Interactive control for **LUFS** (perceived loudness) and **Peak** normalization using FFmpeg.
- **Metadata Mastery:** Automatic embedding of BPM, Key, high-res Album Art, and track duration.
- **Smart Quality Logic:** Automatically detects source quality to prevent upscaling lossy audio into fake lossless files.

### 3. The Export Center (Selective Sync) 📦
Push your crates directly into your favorite DJ software without manual re-scanning:
- **Rekordbox:** Direct `library.xml` generation for Pioneer DJ gear.
- **Engine DJ:** Direct database injection (`m.db`) for Denon/Numark/Rane hardware.
- **Mixxx:** Automated injection into the Mixxx SQLite library (Linux, macOS, Windows).
- **djay Pro / Serato:** "Rich M3U8" generation with extended metadata for mobile and desktop apps.

## Installation

```bash
# Clone the repository
git clone https://github.com/flarkflarkflark/DJwerk.git
cd DJwerk

# Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

## Usage

1. Run the application: `python3 main.py`
2. Configure your **Auth Browser** in Settings -> Connections.
3. Paste a URL or a text block into the main entry.
4. Select your tracks in the **Crate Selector**.
5. Use the **Export Center** to push your tracks to your DJ software.

---
*Part of the flarkAUDIO work suite.*
