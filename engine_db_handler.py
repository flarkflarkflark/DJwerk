import sqlite3
import os
import time
import shutil

class EngineDBHandler:
    def __init__(self, db_path="m.db", dry_run=False):
        """
        Initializeert de verbinding met de Engine DJ SQLite database.
        
        Args:
            db_path (str): Pad naar de m.db database (meestal op een exFAT USB of SD).
            dry_run (bool): Als True, worden er GEEN wijzigingen opgeslagen in de echte DB.
                            Er wordt een temporary in-memory clone of read-only kopie gebruikt
                            om de queries te valideren.
        """
        self.db_path = db_path
        self.dry_run = dry_run
        
        if self.dry_run:
            print(f"[ENGINE_DB] ⚠️ DRY-RUN MODE ACTIEF. Geen wijzigingen aan {self.db_path}.")
            
        self.conn = self._connect()
        if self.conn:
            self._ensure_schema()

    def _connect(self):
        try:
            if self.dry_run:
                # Maak een tijdelijke kopie van de DB in memory of /tmp om queries te valideren
                if os.path.exists(self.db_path):
                    # Voor echt veilige dry-runs: lees de originele DB in memory
                    source = sqlite3.connect(self.db_path)
                    mem_conn = sqlite3.connect(':memory:')
                    source.backup(mem_conn)
                    source.close()
                    return mem_conn
                else:
                    return sqlite3.connect(':memory:')
            else:
                # 🛡️ VEILIGHEID: Altijd pre-sync backup maken voordat we de live DB openen
                self._create_backup()
                return sqlite3.connect(self.db_path)
        except sqlite3.Error as e:
            print(f"[ENGINE_DB] Database connection error: {e}")
            return None

    def _create_backup(self):
        """Maakt een .bak kopie van de database voordat er geschreven wordt."""
        if os.path.exists(self.db_path):
            backup_path = f"{self.db_path}.bak"
            try:
                shutil.copy2(self.db_path, backup_path)
                print(f"[ENGINE_DB] 🛡️ Pre-sync backup gemaakt: {backup_path}")
            except Exception as e:
                print(f"[ENGINE_DB] ❌ Waarschuwing: Kon geen backup maken van {self.db_path}: {e}")

    def _ensure_schema(self):
        """Zorgt dat de tabellen bestaan (alleen nuttig voor dummy/test omgevingen)."""
        if not self.conn:
            return
        
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Track (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    artist TEXT,
                    album TEXT,
                    path TEXT,
                    bpm REAL,
                    key TEXT,
                    dateAdded INTEGER
                )
            ''')
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"[ENGINE_DB] Schema error: {e}")

    def add_track_to_db(self, file_path, metadata) -> bool:
        """
        Voegt een track toe aan de Engine DJ database of update deze als hij al bestaat.
        metadata is een dict met: artist, title, album, bpm, key
        """
        if not self.conn:
            print("[ENGINE_DB] Geen database verbinding.")
            return False

        try:
            cursor = self.conn.cursor()
            
            # Pad validatie: Denon Engine vereist specifieke pad-notaties afhankelijk van het OS, 
            # maar voor nu zoeken we exact op de file_path string.
            cursor.execute("SELECT id FROM Track WHERE path = ?", (file_path,))
            existing = cursor.fetchone()

            artist = metadata.get("artist", "Unknown")
            title = metadata.get("title", "Unknown")
            album = metadata.get("album", "")
            
            # Zorg dat BPM altijd een float is, anders crasht de DB parser op de hardware
            try:
                bpm = float(metadata.get("bpm", 0.0))
            except (ValueError, TypeError):
                bpm = 0.0
                
            key = metadata.get("key", "")
            now = int(time.time())

            if existing:
                # Update bestaande track
                cursor.execute('''
                    UPDATE Track 
                    SET title=?, artist=?, album=?, bpm=?, key=?
                    WHERE id=?
                ''', (title, artist, album, bpm, key, existing[0]))
                action = "geüpdatet in"
            else:
                # Nieuwe track invoegen
                cursor.execute('''
                    INSERT INTO Track (title, artist, album, path, bpm, key, dateAdded)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (title, artist, album, file_path, bpm, key, now))
                action = "toegevoegd aan"

            self.conn.commit()
            
            if self.dry_run:
                print(f"[ENGINE_DB] (DRY-RUN) Track zou zijn {action} m.db: {artist} - {title}")
            else:
                print(f"[ENGINE_DB] Track succesvol {action} m.db: {artist} - {title}")
                
            return True

        except sqlite3.Error as e:
            print(f"[ENGINE_DB] ❌ Database Error bij toevoegen track '{metadata.get('title', 'Unknown')}': {e}")
            if self.conn:
                self.conn.rollback() # Voorkom corrupte transacties
            return False
        except Exception as e:
            print(f"[ENGINE_DB] ❌ Onverwachte fout: {e}")
            return False

    def close(self):
        if self.conn:
            self.conn.close()

if __name__ == "__main__":
    # Test de handler in Dry-Run modus (veilig)
    print("--- Start EngineDBHandler Test (Dry Run) ---")
    handler = EngineDBHandler("dummy_m.db", dry_run=True)
    test_meta = {"artist": "Test Artist", "title": "Test Track", "bpm": "124.5", "key": "8A"}
    success = handler.add_track_to_db("/downloads/test_track.flac", test_meta)
    print(f"Test geslaagd: {success}")
    handler.close()
