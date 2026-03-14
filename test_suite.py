import unittest
from unittest.mock import MagicMock, patch
import sqlite3
import os

# Import the components to test
from djwerk_matcher import SpotifyCrateParser, UniversalMatcher
from djwerk_core import DJwerkCore
from universal_db import UniversalDBHandler
from djwerk_controller import DJwerkController

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

class TestDJwerkCore(unittest.TestCase):
    def setUp(self):
        self.core = DJwerkCore(download_path="test_downloads")

    @patch('yt_dlp.YoutubeDL')
    def test_download_track_with_cookies(self, mock_ydl):
        # Verify that cookies_from_browser is passed to ydl_opts
        self.core.download_track("https://youtube.com/watch?v=123", cookies_from_browser="firefox")
        args, kwargs = mock_ydl.call_args
        ydl_opts = args[0]
        self.assertEqual(ydl_opts['cookiesfrombrowser'], ("firefox",))

class TestDJwerkController(unittest.TestCase):
    def setUp(self):
        self.view = MagicMock()
        self.view.fx_enabled = True
        self.view.cookies_browser = "chrome"
        
        with patch('djwerk_controller.UniversalMatcher'):
            with patch('djwerk_controller.UniversalDBHandler'):
                self.controller = DJwerkController(self.view)

    def test_sync_event_triggers_thread(self):
        self.view.url_entry.get.return_value = "https://spotify.com/track/1"
        with patch('threading.Thread') as mock_thread:
            self.controller.sync_event()
            self.assertTrue(mock_thread.called)

if __name__ == '__main__':
    unittest.main()
