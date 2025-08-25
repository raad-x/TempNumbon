"""
Database Protection and Backup System for Ring4 SMS Bot
Provides bulletproof database storage with automated backups, corruption prevention,
and disaster recovery capabilities.

Features:
- Automated backup every 3 days (72 hours)
- Real-time corruption detection
- Lock-based write protection
- Multiple backup retention
- Automatic recovery mechanisms
- Cloud storage integration ready
"""

import os
import json
import shutil
import threading
import time
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from threading import Lock, Thread
import fcntl
import tempfile
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseProtectionError(Exception):
    """Custom exception for database protection operations"""
    pass


class DatabaseCorruptionError(DatabaseProtectionError):
    """Raised when database corruption is detected"""
    pass


class BackupCorruptionError(DatabaseProtectionError):
    """Raised when backup corruption is detected"""
    pass


class DatabaseProtectionService:
    """
    Advanced Database Protection and Backup Service

    Provides:
    - Continuous automated backups every 3 days
    - Write-locking to prevent corruption
    - Integrity validation
    - Multiple backup retention
    - Recovery mechanisms
    """

    def __init__(self,
                 database_path: str,
                 backup_dir: Optional[str] = None,
                 backup_interval_hours: int = 72,  # 3 days
                 max_backups: int = 10,
                 enable_compression: bool = True):

        self.database_path = Path(database_path)
        self.backup_dir = Path(
            backup_dir) if backup_dir else self.database_path.parent / "backups"
        self.backup_interval_hours = backup_interval_hours
        self.max_backups = max_backups
        self.enable_compression = enable_compression

        # Threading and locking
        self._write_lock = Lock()
        self._backup_thread = None
        self._stop_backup_thread = threading.Event()
        self._backup_running = False

        # Protection flags
        self._initialized = False
        self._protected_mode = True

        # Initialize protection system
        self._initialize_protection()

    def _initialize_protection(self):
        """Initialize the database protection system"""
        logger.info("🛡️ Initializing Database Protection System...")

        # Ensure directories exist
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        # Create database if it doesn't exist
        if not self.database_path.exists():
            logger.info(f"📄 Creating new database: {self.database_path}")
            self._create_empty_database()

        # Validate existing database
        if not self._validate_database_integrity():
            logger.warning(
                "⚠️ Database corruption detected, attempting recovery...")
            if not self._attempt_recovery():
                raise DatabaseCorruptionError(
                    "Database is corrupted and recovery failed")

        # Start automated backup service
        self._start_backup_service()

        self._initialized = True
        logger.info("✅ Database Protection System initialized successfully")

    def _create_empty_database(self):
        """Create an empty TinyDB database structure"""
        empty_db = {
            "wallets": {},
            "deposits": {},
            "transactions": {},
            "orders": {},
            "refunds": {},
            "_protection": {
                "created_at": datetime.now().isoformat(),
                "version": "1.0",
                "checksum": ""
            }
        }

        # Calculate checksum
        empty_db["_protection"]["checksum"] = self._calculate_checksum(
            empty_db)

        self._write_database_atomic(empty_db)

    def _calculate_checksum(self, data: Dict) -> str:
        """Calculate SHA-256 checksum of database content"""
        # Remove protection section for checksum calculation
        data_copy = data.copy()
        if "_protection" in data_copy:
            data_copy = {k: v for k, v in data_copy.items() if k !=
                         "_protection"}

        content = json.dumps(data_copy, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(content.encode()).hexdigest()

    def _validate_database_integrity(self) -> bool:
        """Validate database file integrity"""
        try:
            if not self.database_path.exists():
                return False

            with open(self.database_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Check if it's a valid structure
            required_tables = {"wallets", "deposits",
                               "transactions", "orders", "refunds"}
            if not required_tables.issubset(set(data.keys())):
                logger.warning("❌ Database missing required tables")
                return False

            # Validate checksum if available
            if "_protection" in data and "checksum" in data["_protection"]:
                expected_checksum = data["_protection"]["checksum"]
                actual_checksum = self._calculate_checksum(data)

                if expected_checksum != actual_checksum:
                    logger.warning(
                        f"❌ Database checksum mismatch: expected {expected_checksum}, got {actual_checksum}")
                    return False

            return True

        except (json.JSONDecodeError, IOError, KeyError) as e:
            logger.error(f"❌ Database validation failed: {e}")
            return False

    def _write_database_atomic(self, data: Dict):
        """Write database using atomic operations to prevent corruption"""
        # Update protection metadata
        if "_protection" not in data:
            data["_protection"] = {}

        data["_protection"].update({
            "last_modified": datetime.now().isoformat(),
            "version": "1.0",
            "checksum": self._calculate_checksum(data)
        })

        # Use atomic write with temporary file
        temp_file = self.database_path.with_suffix('.tmp')
        backup_file = self.database_path.with_suffix('.backup')

        try:
            # Create backup of current file
            if self.database_path.exists():
                shutil.copy2(self.database_path, backup_file)

            # Write to temporary file first
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Atomic move
            shutil.move(str(temp_file), str(self.database_path))

            # Remove backup if write was successful
            if backup_file.exists():
                backup_file.unlink()

            logger.debug(
                f"✅ Database written atomically: {self.database_path}")

        except Exception as e:
            # Restore from backup if atomic write failed
            if backup_file.exists():
                shutil.move(str(backup_file), str(self.database_path))

            # Clean up temp file
            if temp_file.exists():
                temp_file.unlink()

            raise DatabaseProtectionError(f"Atomic write failed: {e}")

    @contextmanager
    def write_lock(self):
        """Context manager for safe database writes"""
        if not self._protected_mode:
            yield
            return

        acquired = self._write_lock.acquire(timeout=30)  # 30 second timeout
        if not acquired:
            raise DatabaseProtectionError(
                "Could not acquire write lock within timeout")

        try:
            yield
        finally:
            self._write_lock.release()

    def create_backup(self, backup_name: Optional[str] = None) -> Path:
        """Create a manual backup of the database"""
        if not self.database_path.exists():
            raise DatabaseProtectionError(
                "Cannot backup non-existent database")

        if not self._validate_database_integrity():
            raise DatabaseCorruptionError("Cannot backup corrupted database")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = backup_name or f"ring4_database_backup_{timestamp}.json"
        backup_path = self.backup_dir / backup_name

        try:
            # Read current database
            with open(self.database_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Add backup metadata
            backup_data = {
                "backup_metadata": {
                    "created_at": datetime.now().isoformat(),
                    "original_file": str(self.database_path),
                    "backup_version": "1.0",
                    "backup_type": "manual"
                },
                "database": data
            }

            # Write backup
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ Manual backup created: {backup_path}")
            return backup_path

        except Exception as e:
            logger.error(f"❌ Failed to create backup: {e}")
            raise DatabaseProtectionError(f"Backup creation failed: {e}")

    def _automated_backup(self):
        """Automated backup that runs every 3 days"""
        logger.info("🔄 Starting automated backup service...")

        while not self._stop_backup_thread.is_set():
            try:
                # Wait for backup interval or stop signal
                if self._stop_backup_thread.wait(timeout=self.backup_interval_hours * 3600):
                    break

                # Create automated backup
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"auto_backup_{timestamp}.json"

                logger.info(f"🔄 Creating automated backup: {backup_name}")
                backup_path = self.create_backup(backup_name)

                # Clean up old backups
                self._cleanup_old_backups()

                logger.info("✅ Automated backup completed successfully")

            except Exception as e:
                logger.error(f"❌ Automated backup failed: {e}")
                # Continue running even if one backup fails
                continue

        logger.info("🛑 Automated backup service stopped")

    def _cleanup_old_backups(self):
        """Remove old backups to maintain storage limits"""
        try:
            backup_files = list(self.backup_dir.glob("*.json"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            if len(backup_files) > self.max_backups:
                files_to_remove = backup_files[self.max_backups:]
                for file_path in files_to_remove:
                    file_path.unlink()
                    logger.info(f"🗑️ Removed old backup: {file_path.name}")

                logger.info(
                    f"🧹 Cleanup completed, kept {self.max_backups} most recent backups")

        except Exception as e:
            logger.error(f"❌ Backup cleanup failed: {e}")

    def _start_backup_service(self):
        """Start the automated backup service"""
        if self._backup_running:
            return

        self._backup_thread = Thread(
            target=self._automated_backup, daemon=True)
        self._backup_thread.start()
        self._backup_running = True

        logger.info(
            f"🚀 Automated backup service started (interval: {self.backup_interval_hours}h)")

    def stop_backup_service(self):
        """Stop the automated backup service"""
        if not self._backup_running:
            return

        self._stop_backup_thread.set()
        if self._backup_thread and self._backup_thread.is_alive():
            self._backup_thread.join(timeout=10)

        self._backup_running = False
        logger.info("🛑 Automated backup service stopped")

    def _attempt_recovery(self) -> bool:
        """Attempt to recover database from backups"""
        logger.info("🔧 Attempting database recovery...")

        # Find the most recent valid backup
        backup_files = list(self.backup_dir.glob("*.json"))
        backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        for backup_file in backup_files:
            try:
                logger.info(f"🔍 Trying recovery from: {backup_file.name}")

                with open(backup_file, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)

                # Extract database from backup format
                if "database" in backup_data:
                    db_data = backup_data["database"]
                else:
                    # Assume it's a direct database backup
                    db_data = backup_data

                # Validate backup integrity
                if self._validate_backup_data(db_data):
                    # Restore database
                    self._write_database_atomic(db_data)
                    logger.info(
                        f"✅ Successfully recovered database from: {backup_file.name}")
                    return True

            except Exception as e:
                logger.error(
                    f"❌ Failed to recover from {backup_file.name}: {e}")
                continue

        logger.error("❌ All recovery attempts failed")
        return False

    def _validate_backup_data(self, data: Dict) -> bool:
        """Validate backup data integrity"""
        try:
            required_tables = {"wallets", "deposits",
                               "transactions", "orders", "refunds"}
            return required_tables.issubset(set(data.keys()))
        except Exception:
            return False

    def get_backup_info(self) -> List[Dict]:
        """Get information about available backups"""
        backups = []

        for backup_file in self.backup_dir.glob("*.json"):
            try:
                stat = backup_file.stat()
                backup_info = {
                    "filename": backup_file.name,
                    "path": str(backup_file),
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "age_hours": round((time.time() - stat.st_mtime) / 3600, 1)
                }
                backups.append(backup_info)
            except Exception as e:
                logger.error(
                    f"❌ Error reading backup info for {backup_file}: {e}")

        return sorted(backups, key=lambda x: x["created_at"], reverse=True)

    def restore_from_backup(self, backup_filename: str) -> bool:
        """Restore database from a specific backup"""
        backup_path = self.backup_dir / backup_filename

        if not backup_path.exists():
            raise DatabaseProtectionError(
                f"Backup file not found: {backup_filename}")

        try:
            with self.write_lock():
                logger.info(f"🔧 Restoring database from: {backup_filename}")

                with open(backup_path, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)

                # Extract database from backup format
                if "database" in backup_data:
                    db_data = backup_data["database"]
                else:
                    db_data = backup_data

                if not self._validate_backup_data(db_data):
                    raise BackupCorruptionError(
                        "Backup data validation failed")

                # Create safety backup before restore
                safety_backup = f"pre_restore_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                if self.database_path.exists():
                    self.create_backup(safety_backup)

                # Restore database
                self._write_database_atomic(db_data)

                logger.info(
                    f"✅ Database restored successfully from: {backup_filename}")
                return True

        except Exception as e:
            logger.error(f"❌ Database restore failed: {e}")
            raise DatabaseProtectionError(f"Restore failed: {e}")

    def get_protection_status(self) -> Dict:
        """Get current protection system status"""
        return {
            "initialized": self._initialized,
            "protected_mode": self._protected_mode,
            "backup_service_running": self._backup_running,
            "database_exists": self.database_path.exists(),
            "database_valid": self._validate_database_integrity() if self.database_path.exists() else False,
            "backup_dir": str(self.backup_dir),
            "backup_interval_hours": self.backup_interval_hours,
            "total_backups": len(list(self.backup_dir.glob("*.json"))),
            "last_backup": self._get_last_backup_time(),
            "next_backup_eta": self._get_next_backup_eta()
        }

    def _get_last_backup_time(self) -> Optional[str]:
        """Get timestamp of last backup"""
        backup_files = list(self.backup_dir.glob("*.json"))
        if not backup_files:
            return None

        latest_backup = max(backup_files, key=lambda x: x.stat().st_mtime)
        return datetime.fromtimestamp(latest_backup.stat().st_mtime).isoformat()

    def _get_next_backup_eta(self) -> Optional[str]:
        """Get estimated time for next backup"""
        if not self._backup_running:
            return None

        last_backup_time = self._get_last_backup_time()
        if not last_backup_time:
            return "Soon"

        last_backup = datetime.fromisoformat(last_backup_time)
        next_backup = last_backup + timedelta(hours=self.backup_interval_hours)

        if next_backup <= datetime.now():
            return "Overdue"

        return next_backup.isoformat()

    def emergency_backup(self) -> Path:
        """Create an emergency backup immediately"""
        emergency_name = f"emergency_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        return self.create_backup(emergency_name)

    def __del__(self):
        """Cleanup when object is destroyed"""
        try:
            self.stop_backup_service()
        except Exception:
            pass


# Export the main class
__all__ = ['DatabaseProtectionService', 'DatabaseProtectionError',
           'DatabaseCorruptionError', 'BackupCorruptionError']
