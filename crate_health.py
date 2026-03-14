import os
import difflib
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from datetime import datetime

class CrateHealthScanner:
    def __init__(self, downloads_path="downloads"):
        # Resolve absolute path relative to this file
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.downloads_path = os.path.join(base_dir, downloads_path)
        if not os.path.exists(self.downloads_path):
            os.makedirs(self.downloads_path)

    def scan(self):
        if not os.path.exists(self.downloads_path):
            return {
                "total_files": 0,
                "duplicates": [],
                "low_bitrate": [],
                "missing_art": []
            }

        files = [f for f in os.listdir(self.downloads_path) if f.lower().endswith(('.mp3', '.flac'))]
        
        duplicates = []
        low_bitrate = []
        missing_art = []
        
        # Check for duplicates (same name or very similar)
        # We compare base names without extension
        for i, f1 in enumerate(files):
            n1 = os.path.splitext(f1)[0].lower()
            for f2 in files[i+1:]:
                n2 = os.path.splitext(f2)[0].lower()
                
                if n1 == n2:
                    duplicates.append((f1, f2))
                else:
                    # Check for similar names (e.g. "Track" vs "Track (1)")
                    similarity = difflib.SequenceMatcher(None, n1, n2).ratio()
                    if similarity > 0.9:
                        duplicates.append((f1, f2))

        for f in files:
            path = os.path.join(self.downloads_path, f)
            try:
                if f.lower().endswith('.mp3'):
                    audio = MP3(path)
                    # Bitrate check (bitrate is in bits per second)
                    if audio.info.bitrate < 310000: # Allow some margin for VBR/re-encoding (320kbps target)
                        low_bitrate.append((f, f"{audio.info.bitrate // 1000}kbps"))
                    
                    # Cover art check (ID3v2 APIC tag)
                    has_art = False
                    if audio.tags:
                        for tag in audio.tags.keys():
                            if tag.startswith('APIC'):
                                has_art = True
                                break
                    if not has_art:
                        missing_art.append(f)
                        
                elif f.lower().endswith('.flac'):
                    audio = FLAC(path)
                    # FLAC is lossless, so no bitrate check needed.
                    
                    # Cover art check
                    if not audio.pictures:
                        missing_art.append(f)
            except Exception as e:
                print(f"Error scanning {f}: {e}")

        return {
            "total_files": len(files),
            "duplicates": duplicates,
            "low_bitrate": low_bitrate,
            "missing_art": missing_art
        }

    def generate_report(self):
        results = self.scan()
        report = []
        report.append(f"# Crate Health Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total files scanned: {results['total_files']}")
        report.append("")
        
        if results['duplicates']:
            report.append("## ⚠️ Duplicates Found")
            for d in results['duplicates']:
                report.append(f"- `{d[0]}` <-> `{d[1]}`")
        else:
            report.append("✅ No duplicates found.")
            
        report.append("")
        if results['low_bitrate']:
            report.append("## 📉 Low Bitrate Tracks (< 320kbps)")
            for b in results['low_bitrate']:
                report.append(f"- `{b[0]}` ({b[1]})")
        else:
            report.append("✅ All MP3s are high quality (>= 320kbps).")

        report.append("")
        if results['missing_art']:
            report.append("## 🖼️ Missing Cover Art")
            for m in results['missing_art']:
                report.append(f"- `{m}`")
        else:
            report.append("✅ All tracks have embedded cover art.")
            
        report.append("\n---\n")
        return "\n".join(report)

if __name__ == "__main__":
    scanner = CrateHealthScanner()
    print(scanner.generate_report())
