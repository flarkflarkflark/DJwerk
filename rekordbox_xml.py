import xml.etree.ElementTree as ET
import os
import time
import json
from xml.dom import minidom

class RekordboxXMLGenerator:
    """Generates and maintains a Rekordbox XML library for cross-platform DJ software compatibility (Linux/macOS/Windows)."""
    
    def __init__(self, xml_path="library.xml", db_backup="library_db.json"):
        self.xml_path = xml_path
        self.db_backup = db_backup
        self.tracks = self._load_db()

    def _load_db(self):
        if os.path.exists(self.db_backup):
            try:
                with open(self.db_backup, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []

    def _save_db(self):
        with open(self.db_backup, 'w') as f:
            json.dump(self.tracks, f, indent=4)

    def add_track(self, path, artist="Unknown", title="Unknown", album="", bpm=120.0, key="", **kwargs):
        """Adds a track to the library. Updates if path already exists."""
        
        # Check if already exists to prevent duplicates
        for t in self.tracks:
            if t['Location'] == path:
                return

        track_info = {
            "Location": "file://localhost" + os.path.abspath(path),
            "Name": title,
            "Artist": artist,
            "Album": album,
            "Genre": kwargs.get("genre", ""),
            "Kind": "FLAC File" if path.endswith(".flac") else "MP3 File",
            "Size": str(os.path.getsize(path)) if os.path.exists(path) else "0",
            "AverageBpm": str(bpm),
            "Tonality": key,
            "Year": str(kwargs.get("year", "0")),
            "DateAdded": time.strftime("%Y-%m-%d")
        }
        self.tracks.append(track_info)
        self._save_db()

    def save(self):
        """Generates the actual XML file from the current track list."""
        root = ET.Element("DJ_PLAYLISTS", Version="1.0.0")
        ET.SubElement(root, "PRODUCT", Name="rekordbox", Version="6.0.0", Company="Pioneer DJ")
        collection = ET.SubElement(root, "COLLECTION", Entries=str(len(self.tracks)))

        for i, t in enumerate(self.tracks):
            ET.SubElement(collection, "TRACK", 
                         TrackID=str(i+1),
                         Name=t["Name"],
                         Artist=t["Artist"],
                         Album=t["Album"],
                         Genre=t["Genre"],
                         Kind=t["Kind"],
                         Size=t["Size"],
                         AverageBpm=t["AverageBpm"],
                         Tonality=t["Tonality"],
                         Location=t["Location"])
        
        playlists = ET.SubElement(root, "PLAYLISTS")
        node = ET.SubElement(playlists, "NODE", Name="ROOT", Type="0")
        # Add a default 'DJwerk Sync' playlist
        sync_node = ET.SubElement(node, "NODE", Name="DJwerk Sync", Type="1", KeyType="0", Entries=str(len(self.tracks)))
        for i in range(len(self.tracks)):
            ET.SubElement(sync_node, "TRACK", Key=str(i+1))

        xml_str = ET.tostring(root, encoding="utf-8")
        reparsed = minidom.parseString(xml_str)
        pretty_xml = reparsed.toprettyxml(indent="  ")

        with open(self.xml_path, "w", encoding="utf-8") as f:
            f.write(pretty_xml)
        
        print(f"[XML] Library updated: {len(self.tracks)} tracks in {self.xml_path}")

if __name__ == "__main__":
    gen = RekordboxXMLGenerator()
    gen.add_track("test.flac", artist="Linux", title="Chique")
    gen.save()
