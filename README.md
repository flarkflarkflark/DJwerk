# DJwerk

**DJwerk** is the universal "Physical Crate Engine" of the flarkAUDIO suite. It transforms volatile cloud playlists into a robust, physical, and platform-independent music collection for the professional DJ.

## The Goal: Offline Reliability for DJs
DJs should no longer be dependent on Wi-Fi or streaming subscriptions during a set. DJwerk pulls music from the cloud and converts it into physical files (FLAC/MP3) with universal metadata that works across all hardware and software.

## Core Features

### 1. Universal Input (The Cloud Scrapers)
- **Lossless Sources:** Native FLAC downloads from **Tidal** and **Qobuz**.
- **Playlist Converters:** Intelligent translation from **Spotify** playlists to lossless sources.
- **Underground & Bootlegs:** Integration of **SoundCloud**, **Bandcamp**, and **YouTube** (via yt-dlp).
- **DJ Stores:** Support for purchased tracks from **Beatport** and **Beatsource**.

### 2. The "Crate" Engine (Processing)
- **Normalization:** Converts everything to your standard (e.g., 44.1kHz FLAC or 320kbps MP3).
- **Metadata Mastery:** 
    - Automatic analysis of **BPM** and **Key** (Camelot Wheel).
    - High-res **Album Art** embedding.
    - Title cleanup (stripping "Official Video" junk).
- **Harmonic Mixing:** Full support for **Mixed In Key** standards.
- **STEM-ready:** Optional integration with **STEMwerk** for pre-separation.

### 3. Universal Output (The Destinations)
- **Hardware (Stand-alone):**
    - **Engine OS (Denon/Numark/Rane):** Direct database injection (`m.db`) for the Prime Go and SC-series.
    - **Pioneer DJ / AlphaTheta:** CDJ-ready USB structures and Rekordbox XML export.
- **Software (Performance):**
    - **Algoriddim djay:** Mobile-ready sync for iPad/iPhone (iCloud/Files).
    - **Rekordbox, Serato, Traktor, VirtualDJ, Mixxx:** Universal XML and M3U8 playlists.
- **Creative:**
    - **Ableton Live:** Automatically warped tracks and project exports.
    - **Lexicon:** Compatibility for advanced library management.

## Technical Roadmap
1. **v0.1.0:** Tidal to Engine DJ (Denon Prime Go) basic sync.
2. **v0.2.0:** Spotify Playlist Parser & Metadata Enrichment.
3. **v0.3.0:** Pioneer/Rekordbox XML Export & SoundCloud support.
4. **v0.4.0:** djay Mobile Sync & STEMwerk integration.

## Contact
- **Author:** flarkAUDIO <flarkaudio@pm.me>
- **GitHub:** [flarkflarkflark](https://github.com/flarkflarkflark)

---
*Part of the flarkAUDIO work suite.*
