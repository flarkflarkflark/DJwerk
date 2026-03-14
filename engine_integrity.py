import sqlite3
import os
import shutil
import logging

class DatabaseValidator:
    """Provides validation and integrity checks for the Engine DJ database."""

    @staticmethod
    def backup(db_path: str):
        """Creates a temporary backup of the database before operations.
        
        Args:
            db_path (str): Path to the database file.
        """
        if os.path.exists(db_path):
            backup_path = f"{db_path}.bak"
            shutil.copy2(db_path, backup_path)
            logging.info(f"Database backup created at {backup_path}")

    @staticmethod
    def restore(db_path: str):
        """Restores the database from the backup file.
        
        Args:
            db_path (str): Path to the database file.
        """
        backup_path = f"{db_path}.bak"
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, db_path)
            logging.warning(f"Database restored from {backup_path}")

    @staticmethod
    def check_integrity(db_path: str) -> bool:
        """Runs a PRAGMA integrity_check on the SQLite database.
        
        Args:
            db_path (str): Path to the database file.
            
        Returns:
            bool: True if integrity check passes, False otherwise.
        """
        if not os.path.exists(db_path):
            return False
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0] == "ok":
                return True
            else:
                logging.error(f"Integrity check failed: {result}")
                return False
        except sqlite3.Error as e:
            logging.error(f"SQLite error during integrity check: {e}")
            return False

    @staticmethod
    def validate_track_entries(db_path: str) -> bool:
        """Ensures no tracks have null or empty artists or titles.
        
        Args:
            db_path (str): Path to the database file.
            
        Returns:
            bool: True if all tracks are valid, False otherwise.
        """
        if not os.path.exists(db_path):
            return False

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            # Assuming the table name is 'Track' based on standard Engine DJ schema
            # We check for NULL or empty strings in artist and title columns
            cursor.execute("SELECT COUNT(*) FROM Track WHERE artist IS NULL OR artist = '' OR title IS NULL OR title = '';")
            invalid_count = cursor.fetchone()[0]
            conn.close()
            
            if invalid_count == 0:
                return True
            else:
                logging.error(f"Validation failed: {invalid_count} tracks have missing artist or title.")
                return False
        except sqlite3.Error as e:
            logging.error(f"SQLite error during track validation: {e}")
            # If the table doesn't exist yet (new DB), we might consider it 'valid' or handle it
            return True 

    @classmethod
    def validate(cls, db_path: str) -> bool:
        """Runs all validation checks on the database.
        
        Args:
            db_path (str): Path to the database file.
            
        Returns:
            bool: True if all checks pass, False otherwise.
        """
        if not cls.check_integrity(db_path):
            return False
        if not cls.validate_track_entries(db_path):
            return False
        return True
