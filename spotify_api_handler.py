import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
import json

class SpotifyApiHandler:
    def __init__(self, client_id=None, client_secret=None, cache_path=".spotify_cache"):
        self.client_id = client_id or os.getenv("SPOTIFY_CLIENT_ID", "your_client_id")
        self.client_secret = client_secret or os.getenv("SPOTIFY_CLIENT_SECRET", "your_client_secret")
        self.redirect_uri = "http://localhost:8888/callback"
        self.cache_path = cache_path
        self.sp = None

    def _join_artists(self, artists):
        seen = set()
        cleaned = []
        for artist in artists:
            name = artist.get('name')
            if not name:
                continue
            name = str(name).strip()
            if not name:
                continue
            lowered = name.lower()
            if lowered in {"na", "n/a", "unknown", "unknown artist"}:
                continue
            if lowered in seen:
                continue
            seen.add(lowered)
            cleaned.append(name)
        return " & ".join(cleaned) if cleaned else "Unknown Artist"

    def update_credentials(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret

    def logout(self):
        """Clears the session and deletes the cache file."""
        self.sp = None
        if os.path.exists(self.cache_path):
            os.remove(self.cache_path)
        print("[SPOTIFY] Logged out and cache removed.")

    def get_username(self):
        """Returns the display name of the logged-in user."""
        if self.sp or self.check_login():
            try:
                me = self.sp.current_user()
                return me.get('display_name') or me.get('id')
            except:
                return "Active Session"
        return None

    def check_login(self):
        """Checks if a valid Spotify session exists in cache."""
        if os.path.exists(self.cache_path):
            try:
                auth_manager = SpotifyOAuth(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    redirect_uri=self.redirect_uri,
                    cache_path=self.cache_path,
                    open_browser=False
                )
                if auth_manager.get_cached_token():
                    self.sp = spotipy.Spotify(auth_manager=auth_manager)
                    return True
            except:
                pass
        return False

    def get_auth_url(self):
        """Returns the URL for the user to visit to authorize the app."""
        auth_manager = SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope="playlist-read-private user-library-read",
            cache_path=self.cache_path,
            open_browser=False
        )
        return auth_manager.get_authorize_url()

    def complete_login(self, response_url):
        """Completes the login using the URL the user was redirected to."""
        auth_manager = SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            cache_path=self.cache_path
        )
        code = auth_manager.parse_response_code(response_url)
        token_info = auth_manager.get_access_token(code)
        if token_info:
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            return True
        return False

    def get_playlist_tracks(self, playlist_id):
        """Gets ALL tracks from a Spotify playlist using pagination (chique!)."""
        if not self.sp and not self.check_login():
            return []
            
        try:
            results = self.sp.playlist_tracks(playlist_id)
            tracks = results['items']
            # Pagineren tot we alles hebben (voor 511+ tracks)
            while results['next']:
                results = self.sp.next(results)
                tracks.extend(results['items'])
                
            formatted = []
            for item in tracks:
                t = item['track']
                if not t: continue
                formatted.append({
                    'artist': self._join_artists(t.get('artists', [])),
                    'title': t['name'],
                    'album': t['album']['name'],
                    'duration': t.get('duration_ms', 0) / 1000.0,
                    'is_lossless': False, # Spotify is altijd lossy (Ogg/Vorbis)
                    'is_playlist': True,
                    'id': t['id'],
                    'source': 'Spotify'
                })
            return formatted
        except Exception as e:
            print(f"[SPOTIFY] API Error (Playlist): {e}")
            return []

    def get_album_tracks(self, album_id):
        """Gets ALL tracks from a Spotify album."""
        if not self.sp and not self.check_login():
            return []
            
        try:
            album_info = self.sp.album(album_id)
            results = self.sp.album_tracks(album_id)
            tracks = results['items']
            while results['next']:
                results = self.sp.next(results)
                tracks.extend(results['items'])
                
            formatted = []
            for t in tracks:
                formatted.append({
                    'artist': self._join_artists(t.get('artists', [])),
                    'title': t['name'],
                    'album': album_info['name'],
                    'duration': t.get('duration_ms', 0) / 1000.0,
                    'is_lossless': False,
                    'is_playlist': True,
                    'id': t['id'],
                    'source': 'Spotify',
                    'playlist_cover': album_info.get('images', [{}])[0].get('url', '')
                })
            return formatted
        except Exception as e:
            print(f"[SPOTIFY] API Error (Album): {e}")
            return []
