from dataclasses import dataclass
from typing import Optional

@dataclass
class TrackMetadata:
    """Represents a track's metadata for DJ software synchronization.
    
    Attributes:
        artist (str): The name of the artist.
        title (str): The title of the track.
        album (Optional[str]): The album name. Defaults to None.
        year (Optional[int]): The release year. Defaults to None.
        cover_url (Optional[str]): The URL to the track's cover art. Defaults to None.
        spotify_id (Optional[str]): The Spotify track ID. Defaults to None.
        uri (Optional[str]): The Spotify URI. Defaults to None.
        bpm (Optional[float]): The tempo of the track in BPM. Defaults to 120.0.
        key (Optional[str]): The musical key of the track. Defaults to None.
    """
    artist: str
    title: str
    album: Optional[str] = None
    year: Optional[int] = None
    cover_url: Optional[str] = None
    spotify_id: Optional[str] = None
    uri: Optional[str] = None
    bpm: Optional[float] = 120.0
    key: Optional[str] = None

    def to_dict(self):
        """Converts the TrackMetadata instance to a dictionary.
        
        Returns:
            dict: A dictionary representation of the metadata.
        """
        return {
            "artist": self.artist,
            "title": self.title,
            "album": self.album,
            "year": self.year,
            "cover_url": self.cover_url,
            "spotify_id": self.spotify_id,
            "uri": self.uri,
            "bpm": self.bpm,
            "key": self.key
        }
