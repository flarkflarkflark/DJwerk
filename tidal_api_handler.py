import tidalapi
import os
import json
import time
from datetime import datetime

class TidalApiHandler:
    def __init__(self, token_path=".tidal_token.json"):
        self.session = tidalapi.Session()
        self.token_path = token_path
        self.logged_in = False
        self._login_in_progress = False

    def check_login(self):
        """Checks if a valid session exists or can be restored."""
        if os.path.exists(self.token_path):
            try:
                with open(self.token_path, 'r') as f:
                    data = json.load(f)
                
                expiry = data.get('expiry_time')
                expiry_dt = None
                if expiry:
                    try:
                        expiry_dt = datetime.fromtimestamp(float(expiry))
                    except:
                        expiry_dt = None

                # Use the correct method for OAuth session restoration
                success = self.session.load_oauth_session(
                    token_type=data['token_type'],
                    access_token=data['access_token'],
                    refresh_token=data.get('refresh_token'),
                    expiry_time=expiry_dt
                )
                
                if success and self.session.check_login():
                    self.logged_in = True
                    print(f"[TIDAL] Session restored.")
                    return True
            except Exception as e:
                print(f"[TIDAL] Token restore failed: {e}")
        return False

    def start_login_flow(self, callback_func):
        if self._login_in_progress:
            return False
            
        self._login_in_progress = True
        print("[TIDAL] Starting OAuth Device flow...")
        
        try:
            login_key, future = self.session.login_oauth()
            verification_url = f"https://{login_key.verification_uri_complete}"
            user_code = login_key.user_code
            
            if callback_func:
                callback_func(verification_url, user_code)
            
            # We wait for the future, but also check the session manually in a loop
            # as a fallback if the library hangs.
            start_time = time.time()
            while not future.done() and time.time() - start_time < 300:
                if self.session.check_login():
                    print("[TIDAL] Login detected via manual check!")
                    break
                time.sleep(2)
            
            if self.session.check_login():
                self._save_session()
                self.logged_in = True
                self._login_in_progress = False
                return True
                
        except Exception as e:
            print(f"[TIDAL] Login flow error: {e}")
        
        self._login_in_progress = False
        return False

    def _save_session(self):
        expiry = self.session.expiry_time
        expiry_val = expiry.timestamp() if hasattr(expiry, 'timestamp') else str(expiry)

        data = {
            'token_type': self.session.token_type,
            'access_token': self.session.access_token,
            'refresh_token': self.session.refresh_token,
            'expiry_time': expiry_val
        }
        with open(self.token_path, 'w') as f:
            json.dump(data, f)

    def logout(self):
        """Clears the session and deletes the token file."""
        self.session = tidalapi.Session()
        self.logged_in = False
        if os.path.exists(self.token_path):
            os.remove(self.token_path)
        print("[TIDAL] Logged out and token removed.")

    def get_username(self):
        """Returns the username or email of the logged-in user."""
        if self.logged_in and self.session.check_login():
            try:
                # The user object usually has the email/username
                return self.session.user.id
            except:
                return "Active Session"
        return None

    def get_playlist_tracks(self, playlist_id):
        if not self.logged_in and not self.check_login():
            return []
            
        try:
            playlist = self.session.playlist(playlist_id)
            playlist_name = playlist.name if hasattr(playlist, 'name') else "Tidal Playlist"
            # We halen de cover op zonder width argument (niet ondersteund in deze library versie)
            playlist_cover = playlist.image() if hasattr(playlist, 'image') else ""
            tracks = playlist.tracks()
            
            return self._format_tidal_tracks(tracks, playlist_name, playlist_cover)
        except Exception as e:
            print(f"[TIDAL] Playlist Error: {e}")
            return []

    def get_mix_tracks(self, mix_id):
        if not self.logged_in and not self.check_login():
            return []
            
        try:
            mix = self.session.mix(mix_id)
            mix_name = mix.title if hasattr(mix, 'title') else "Tidal Mix"
            mix_cover = mix.image() if hasattr(mix, 'image') else ""
            tracks = mix.items()
            
            return self._format_tidal_tracks(tracks, mix_name, mix_cover)
        except Exception as e:
            print(f"[TIDAL] Mix Error: {e}")
            return []

    def _format_tidal_tracks(self, tracks, collection_name, cover):
        formatted_tracks = []
        for t in tracks:
            # Tidal metadata quality is not a guarantee of downloadable source quality.
            quality = getattr(t, 'audio_quality', 'LOW')
            artists = getattr(t, 'artists', None) or []
            seen = set()
            artist_names = []
            for a in artists:
                name = getattr(a, 'name', None)
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
                artist_names.append(name)
            if not artist_names and getattr(t, "artist", None):
                fallback_name = getattr(t.artist, "name", None)
                if fallback_name:
                    artist_names = [fallback_name]
            artist_display = " & ".join(artist_names) if artist_names else "Unknown Artist"
            
            formatted_tracks.append({
                'artist': artist_display,
                'title': t.name,
                'album': collection_name,
                'is_lossless': False,
                'reported_quality': quality,
                'is_playlist': True,
                'id': t.id,
                'duration': t.duration,
                'bpm': getattr(t, 'bpm', 0),
                'key': getattr(t, 'key', '') or getattr(t, 'mix', ''),
                'source': 'Tidal',
                'playlist_cover': cover
            })
        return formatted_tracks
