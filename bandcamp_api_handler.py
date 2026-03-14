from bandcamp_api import Bandcamp
import os
import json

class BandcampApiHandler:
    def __init__(self):
        self.bc = Bandcamp()
        self.username = None
        self.logged_in = False

    def login(self, username):
        """Bandcamp 'login' usually just means identifying the user to scrape their collection."""
        self.username = username
        try:
            # We checken of de user bestaat door hun profiel te pingen
            profile = self.bc.get_user(username)
            if profile:
                self.logged_in = True
                return True
        except:
            pass
        return False

    def get_collection_tracks(self):
        """Scrapes the user's purchased collection."""
        if not self.logged_in or not self.username:
            return []
            
        try:
            collection = self.bc.get_collection(self.username)
            tracks = []
            for item in collection:
                # Bandcamp API items kunnen albums of tracks zijn
                tracks.append({
                    'artist': item.get('artist', 'Unknown Artist'),
                    'title': item.get('item_title', 'Unknown Title'),
                    'album': item.get('album_title', ''),
                    'is_lossless': True,
                    'is_playlist': True,
                    'id': item.get('item_id'),
                    'url': item.get('item_url')
                })
            return tracks
        except Exception as e:
            print(f"[BANDCAMP] Collection Error: {e}")
            return []

if __name__ == "__main__":
    # Test
    api = BandcampApiHandler()
    # api.login("your_username")
