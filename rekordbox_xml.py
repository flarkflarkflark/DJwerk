import xml.etree.ElementTree as ET
import os
import time
from xml.dom import minidom

class RekordboxXMLGenerator:
    def __init__(self, xml_path="rekordbox.xml"):
        self.xml_path = xml_path
        self.tracks = []

    def add_track(self, file_path, metadata):
        """
        Voegt een track toe aan de interne lijst voor de XML.
        metadata: {artist, title, album, bpm, key, genre, year}
        """
        track_info = {
            "Location": "file://localhost/" + os.path.abspath(file_path).replace("\\", "/"),
            "Name": metadata.get("title", "Unknown"),
            "Artist": metadata.get("artist", "Unknown"),
            "Album": metadata.get("album", ""),
            "Genre": metadata.get("genre", ""),
            "Kind": "FLAC File" if file_path.endswith(".flac") else "MP3 File",
            "Size": str(os.path.getsize(file_path)) if os.path.exists(file_path) else "0",
            "AverageBpm": str(metadata.get("bpm", "0")),
            "Tonality": metadata.get("key", ""),
            "Year": str(metadata.get("year", "0")),
            "DateAdded": time.strftime("%Y-%m-%d")
        }
        self.tracks.append(track_info)

    def generate(self):
        """Genereert het rekordbox.xml bestand volgens de Pioneer specificatie."""
        root = ET.Element("DJ_PLAYLISTS", Version="1.0.0")
        product = ET.SubElement(root, "PRODUCT", Name="rekordbox", Version="6.0.0", Company="Pioneer DJ")
        collection = ET.SubElement(root, "COLLECTION", Entries=str(len(self.tracks)))

        for i, t in enumerate(self.tracks):
            track_elem = ET.SubElement(collection, "TRACK", 
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
        
        # Playlists sectie (leeg voor nu, maar vereist)
        playlists = ET.SubElement(root, "PLAYLISTS")
        node = ET.SubElement(playlists, "NODE", Name="ROOT", Type="0")
        
        # Pretty print de XML
        xml_str = ET.tostring(root, encoding="utf-8")
        reparsed = minidom.parseString(xml_str)
        pretty_xml = reparsed.toprettyxml(indent="  ")

        with open(self.xml_path, "w", encoding="utf-8") as f:
            f.write(pretty_xml)
        
        print(f"[REKORDBOX_XML] XML gegenereerd op: {self.xml_path}")

if __name__ == "__main__":
    # Test
    gen = RekordboxXMLGenerator("test_rekordbox.xml")
    gen.add_track("downloads/test.flac", {"artist": "Test", "title": "Track", "bpm": 128, "key": "4A"})
    gen.generate()
