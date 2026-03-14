import unittest
from unittest.mock import MagicMock, patch, mock_open
import sqlite3
import os
import time
import threading

# Import the components to test
from djwerk_matcher import SpotifyCrateParser
from djwerk_core import DJwerkCore
from universal_db import UniversalDBHandler
from djwerk_controller import DJwerkController
from models.track import TrackMetadata

class TestUniversalDBHandler(unittest.TestCase):
    def setUp(self):
        self.db_file = "test_universal.db"
        self.db = UniversalDBHandler(self.db_file)

    def tearDown(self):
        if os.path.exists(self.db_file):
            os.remove(self.db_file)

    def test_inject_engine_dj(self):
        meta = {"title": "Test", "artist": "Art", "bpm": 120}
        success = self.db.inject_engine_dj("path.flac", meta)
        self.assertTrue(success)
        
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT title FROM Track WHERE path='path.flac'")
        row = cursor.fetchone()
        self.assertEqual(row[0], "Test")
        conn.close()

    def test_inject_all_stubs(self):
        meta = {"title": "Test"}
        results = self.db.add_track_to_all("test.mp3", meta)
        self.assertTrue(results['engine'])
        self.assertTrue(results['serato'])
        self.assertTrue(results['traktor'])
        self.assertTrue(results['virtualdj'])

    def test_mobile_sync(self):
        result = self.db.mobile_sync_cloud_upload("test.flac")
        self.assertEqual(result["status"], "uploaded")

class TestDeepCore(unittest.TestCase):
    def setUp(self):
        self.core = DJwerkCore("test_downloads")

    def test_scrapers(self):
        self.assertEqual(self.core.scrape_deezer("q")["source"], "deezer")
        self.assertEqual(self.core.scrape_bandcamp("q")["source"], "bandcamp")
        self.assertEqual(self.core.scrape_beatport("q")["source"], "beatport")

    def test_fingerprint(self):
        fp = self.core.generate_acoustic_fingerprint("test.flac")
        self.assertTrue(fp.startswith("FINGERPRINT_"))

    def test_auto_cue(self):
        cues = self.core.calculate_auto_cue("test.flac")
        self.assertIn("intro_cue", cues)
        self.assertIn("drop_cue", cues)

    def test_energy_analysis(self):
        energy = self.core.analyze_energy("test.flac")
        self.assertGreaterEqual(energy, 0.0)
        self.assertLessEqual(energy, 1.0)

class TestSpotifyCrateParser(unittest.TestCase):
    def setUp(self):
        with patch('djwerk_matcher.SpotifyOAuth'):
            with patch('spotipy.Spotify'):
                self.parser = SpotifyCrateParser()
                self.parser.sp = MagicMock()

    def test_invalid_url(self):
        """Test with malformed URLs."""
        result = self.parser.parse_url("https://not-spotify.com/abc")
        self.assertEqual(result["type"], "unknown")
        
        tracks = self.parser.get_tracks("https://not-spotify.com/abc")
        self.assertEqual(tracks, [])

    def test_missing_metadata(self):
        """Test tracks with missing metadata fields."""
        mock_track = {
            'artists': [{'name': 'Test Artist'}],
            'name': 'Test Title',
            'id': '123',
            'uri': 'spotify:track:123',
            'album': {
                # Missing name, images, release_date
            }
        }
        formatted = self.parser._format_track(mock_track)
        self.assertEqual(formatted['album'], 'Unknown Album')
        self.assertEqual(formatted['cover_url'], '')
        self.assertEqual(formatted['year'], 0)

class TestDJwerkCore(unittest.TestCase):
    def setUp(self):
        self.core = DJwerkCore(download_path="test_downloads")

    @patch('yt_dlp.YoutubeDL')
    def test_failed_download(self, mock_ydl):
        instance = mock_ydl.return_value.__enter__.return_value
        instance.extract_info.side_effect = Exception("Download Failed")
        
        success, message = self.core.download_track("https://youtube.com/watch?v=123")
        self.assertFalse(success)
        self.assertIn("Download Failed", message)

class TestDJwerkController(unittest.TestCase):
    def setUp(self):
        self.mock_view = MagicMock()
        
        self.patcher_matcher = patch('djwerk_controller.SpotifyCrateParser')
        self.patcher_core = patch('djwerk_controller.DJwerkCore')
        self.patcher_db = patch('djwerk_controller.UniversalDBHandler')
        self.patcher_xml = patch('djwerk_controller.RekordboxXMLGenerator')
        self.patcher_health = patch('djwerk_controller.CrateHealthScanner')

        self.mock_matcher_cls = self.patcher_matcher.start()
        self.mock_core_cls = self.patcher_core.start()
        self.mock_db_cls = self.patcher_db.start()
        self.mock_xml_cls = self.patcher_xml.start()
        self.mock_health_cls = self.patcher_health.start()

        self.controller = DJwerkController(self.mock_view)
        self.mock_matcher = self.controller.matcher
        self.mock_core = self.controller.core

    def tearDown(self):
        self.patcher_matcher.stop()
        self.patcher_core.stop()
        self.patcher_db.stop()
        self.patcher_xml.stop()
        self.patcher_health.stop()

    def test_process_sync_no_crash_on_matcher_failure(self):
        self.mock_matcher.get_tracks.side_effect = Exception("API Down")
        try:
            self.controller.process_sync("https://open.spotify.com/track/123")
        except Exception as e:
            self.fail(f"process_sync raised {type(e).__name__} unexpectedly!")
        self.mock_view.log_message.assert_any_call("[FATAL] Matcher failed: API Down")

if __name__ == '__main__':
    unittest.main()
