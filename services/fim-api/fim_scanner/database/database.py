"""
Database Manager for File Integrity Monitoring (FIM) System
Handles all database operations for the FIM application
"""

import sqlite3
import json
import logging
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database operations for the FIM system"""
    
    def __init__(self, config_path: str):
        """
        Initialize DatabaseManager
        
        Args:
            config_path: Path to database configuration JSON file
        """
        self.config_path = config_path
        self.connection = None
        self.db_path = None
        self.timeout = 5.0
        
        # Load configuration
        self._load_config()
    
    def _load_config(self):
        """Load database configuration from JSON file"""
        try:
            if not os.path.exists(self.config_path):
                logger.error(f"Database config file not found: {self.config_path}")
                raise FileNotFoundError(f"Config file not found: {self.config_path}")
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            db_config = config.get('database', {})
            self.db_path = db_config.get('path', '/app/data/fim_database.db')
            self.timeout = db_config.get('timeout', 5.0)
            
            # Ensure database directory exists
            db_dir = os.path.dirname(self.db_path)
            os.makedirs(db_dir, exist_ok=True)
            
            logger.info(f"Database configuration loaded: {self.db_path}")
            
        except Exception as e:
            logger.error(f"Failed to load database configuration: {e}")
            raise
    
    def connect(self):
        """Establish database connection and create tables if needed"""
        try:
            logger.info(f"Connecting to database: {self.db_path}")
            self.connection = sqlite3.connect(self.db_path, timeout=self.timeout)
            self.connection.row_factory = sqlite3.Row  # Enable row access by column name
            
            # Enable WAL mode for better performance
            cursor = self.connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            
            # Create tables if they don't exist
            self._create_tables()
            
            logger.info("Database connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed")
    
    def _create_tables(self):
        """Create database tables if they don't exist"""
        try:
            cursor = self.connection.cursor()
            
            # Files table for storing file baseline information
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS monitored_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE NOT NULL,
                    policy_name TEXT NOT NULL DEFAULT 'default',
                    baseline_hash TEXT,
                    hash_algorithm TEXT NOT NULL DEFAULT 'sha256',
                    baseline_permissions TEXT,
                    baseline_owner_user TEXT,
                    baseline_owner_group TEXT,
                    baseline_size INTEGER,
                    baseline_creation_time REAL NOT NULL,
                    last_scanned_time REAL,
                    status TEXT NOT NULL DEFAULT 'OK',
                    created_at REAL NOT NULL DEFAULT (strftime('%s', 'now')),
                    updated_at REAL NOT NULL DEFAULT (strftime('%s', 'now'))
                )
            """)
            
            # Events table for logging file system events
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS change_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    monitored_file_id INTEGER,
                    file_path TEXT NOT NULL,
                    event_time REAL NOT NULL,
                    event_type TEXT NOT NULL,
                    description TEXT,
                    previous_value TEXT,
                    new_value TEXT,
                    old_hash TEXT,
                    new_hash TEXT,
                    file_size INTEGER,
                    process_name TEXT,
                    process_id INTEGER,
                    user_name TEXT,
                    created_at REAL NOT NULL DEFAULT (strftime('%s', 'now')),
                    FOREIGN KEY (monitored_file_id) REFERENCES monitored_files (id) ON DELETE CASCADE
                )
            """)
            
            # Check if columns exist before creating indexes
            cursor.execute("PRAGMA table_info(monitored_files);")
            monitored_files_columns = [column[1] for column in cursor.fetchall()]
            
            cursor.execute("PRAGMA table_info(change_log);")
            change_log_columns = [column[1] for column in cursor.fetchall()]
            
            # Create indexes for performance - only if columns exist
            indexes = []
            
            if 'file_path' in monitored_files_columns:
                indexes.append("CREATE INDEX IF NOT EXISTS idx_monitored_files_path ON monitored_files(file_path);")
            if 'policy_name' in monitored_files_columns:
                indexes.append("CREATE INDEX IF NOT EXISTS idx_monitored_files_policy ON monitored_files(policy_name);")
            
            if 'monitored_file_id' in change_log_columns:
                indexes.append("CREATE INDEX IF NOT EXISTS idx_change_log_file_id ON change_log(monitored_file_id);")
            if 'file_path' in change_log_columns:
                indexes.append("CREATE INDEX IF NOT EXISTS idx_change_log_file_path ON change_log(file_path);")
            if 'event_time' in change_log_columns:
                indexes.append("CREATE INDEX IF NOT EXISTS idx_change_log_event_time ON change_log(event_time);")
            if 'event_type' in change_log_columns:
                indexes.append("CREATE INDEX IF NOT EXISTS idx_change_log_event_type ON change_log(event_type);")
            
            for index_query in indexes:
                try:
                    cursor.execute(index_query)
                except Exception as e:
                    logger.warning(f"Failed to create index: {index_query} - {e}")
            
            self.connection.commit()
            logger.info("Database tables and indexes created/verified successfully")
            
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            self.connection.rollback()
            raise
    
    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get file information from database"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT * FROM monitored_files WHERE file_path = ?
            """, (file_path,))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get file info for {file_path}: {e}")
            return None
    
    def update_file_info(self, file_path: str, checksum: str, file_size: int = None):
        """Update or insert file information in database"""
        try:
            cursor = self.connection.cursor()
            current_time = datetime.now().timestamp()
            
            # Get file stats if available
            if file_size is None and os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
            
            # Check if file already exists
            existing = self.get_file_info(file_path)
            
            if existing:
                # Update existing record
                cursor.execute("""
                    UPDATE monitored_files 
                    SET baseline_hash = ?, baseline_size = ?, last_scanned_time = ?, 
                        updated_at = ?, status = 'OK'
                    WHERE file_path = ?
                """, (checksum, file_size, current_time, current_time, file_path))
            else:
                # Insert new record
                cursor.execute("""
                    INSERT INTO monitored_files 
                    (file_path, baseline_hash, baseline_size, baseline_creation_time, 
                     last_scanned_time, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, 'OK', ?, ?)
                """, (file_path, checksum, file_size, current_time, current_time, current_time, current_time))
            
            self.connection.commit()
            logger.debug(f"Updated file info for: {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to update file info for {file_path}: {e}")
            self.connection.rollback()
    
    def remove_file_info(self, file_path: str):
        """Remove file information from database"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM monitored_files WHERE file_path = ?", (file_path,))
            self.connection.commit()
            logger.debug(f"Removed file info for: {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to remove file info for {file_path}: {e}")
            self.connection.rollback()
    
    def record_event(self, event_data: Dict[str, Any]):
        """Record a file system event"""
        try:
            cursor = self.connection.cursor()
            
            # Get monitored_file_id if available
            file_path = event_data.get('file_path')
            monitored_file_id = None
            if file_path:
                file_info = self.get_file_info(file_path)
                if file_info:
                    monitored_file_id = file_info['id']
            
            cursor.execute("""
                INSERT INTO change_log 
                (monitored_file_id, file_path, event_time, event_type, description,
                 previous_value, new_value, old_hash, new_hash, file_size)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                monitored_file_id,
                event_data.get('file_path'),
                datetime.fromisoformat(event_data.get('timestamp', datetime.now().isoformat())).timestamp(),
                event_data.get('event_type'),
                event_data.get('description'),
                event_data.get('previous_value'),
                event_data.get('new_value'),
                event_data.get('old_hash'),
                event_data.get('new_hash'),
                event_data.get('file_size')
            ))
            
            self.connection.commit()
            logger.debug(f"Recorded event: {event_data.get('event_type')} for {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to record event: {e}")
            self.connection.rollback()
    
    def get_events(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get recent events from database"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT * FROM change_log 
                ORDER BY event_time DESC 
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get events: {e}")
            return []
    
    def get_events_count(self) -> int:
        """Get total count of events"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM change_log")
            result = cursor.fetchone()
            return result[0] if result else 0
            
        except Exception as e:
            logger.error(f"Failed to get events count: {e}")
            return 0
    
    def get_monitored_files_count(self) -> int:
        """Get count of monitored files"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM monitored_files")
            result = cursor.fetchone()
            return result[0] if result else 0
            
        except Exception as e:
            logger.error(f"Failed to get monitored files count: {e}")
            return 0
    
    def get_all_files(self) -> List[Dict[str, Any]]:
        """Get list of all monitored files"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT id, file_path, baseline_hash as checksum, status, 
                       last_scanned_time, baseline_size, 
                       datetime(created_at, 'unixepoch') as created_at,
                       datetime(updated_at, 'unixepoch') as updated_at
                FROM monitored_files 
                ORDER BY file_path
            """)
            
            rows = cursor.fetchall()
            files = []
            for row in rows:
                file_dict = dict(row)
                # Format timestamps
                if file_dict.get('last_scanned_time'):
                    file_dict['last_scanned'] = datetime.fromtimestamp(file_dict['last_scanned_time']).strftime('%Y-%m-%d %H:%M:%S')
                else:
                    file_dict['last_scanned'] = 'Never'
                files.append(file_dict)
            
            return files
            
        except Exception as e:
            logger.error(f"Failed to get all files: {e}")
            return []
    
    def get_last_scan_time(self) -> Optional[str]:
        """Get timestamp of last scan"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT MAX(last_scanned_time) FROM monitored_files 
                WHERE last_scanned_time IS NOT NULL
            """)
            
            result = cursor.fetchone()
            if result and result[0]:
                return datetime.fromtimestamp(result[0]).isoformat()
            return None
            
        except Exception as e:
            logger.error(f"Failed to get last scan time: {e}")
            return None
    
    def cleanup_old_events(self, days_to_keep: int = 30):
        """Clean up old events from database"""
        try:
            cursor = self.connection.cursor()
            cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
            
            cursor.execute("DELETE FROM change_log WHERE event_time < ?", (cutoff_time,))
            deleted_count = cursor.rowcount
            
            self.connection.commit()
            logger.info(f"Cleaned up {deleted_count} old events (older than {days_to_keep} days)")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old events: {e}")
            self.connection.rollback()
    
    def get_recent_events_formatted(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent events with formatted timestamps and additional details"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT cl.*, 
                       datetime(cl.event_time, 'unixepoch') as formatted_time,
                       mf.status as file_status
                FROM change_log cl
                LEFT JOIN monitored_files mf ON cl.file_path = mf.file_path
                ORDER BY cl.event_time DESC 
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            events = []
            for row in rows:
                event_dict = dict(row)
                # Calculate time ago
                event_time = datetime.fromtimestamp(event_dict['event_time'])
                time_diff = datetime.now() - event_time
                
                if time_diff.days > 0:
                    event_dict['time_ago'] = f"{time_diff.days} gün önce"
                elif time_diff.seconds > 3600:
                    hours = time_diff.seconds // 3600
                    event_dict['time_ago'] = f"{hours} saat önce"
                elif time_diff.seconds > 60:
                    minutes = time_diff.seconds // 60
                    event_dict['time_ago'] = f"{minutes} dakika önce"
                else:
                    event_dict['time_ago'] = "Az önce"
                
                # Format file size
                if event_dict.get('file_size'):
                    size = event_dict['file_size']
                    if size > 1024*1024:
                        event_dict['file_size_formatted'] = f"{size/(1024*1024):.1f} MB"
                    elif size > 1024:
                        event_dict['file_size_formatted'] = f"{size/1024:.1f} KB"
                    else:
                        event_dict['file_size_formatted'] = f"{size} B"
                else:
                    event_dict['file_size_formatted'] = "Bilinmiyor"
                
                # Extract filename from path
                event_dict['filename'] = os.path.basename(event_dict['file_path'])
                
                events.append(event_dict)
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to get formatted events: {e}")
            return []

    def get_file_categories(self) -> Dict[str, int]:
        """Get file counts by category/extension"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN file_path LIKE '%.py' THEN 'Python'
                        WHEN file_path LIKE '%.js' THEN 'JavaScript'
                        WHEN file_path LIKE '%.html' THEN 'HTML'
                        WHEN file_path LIKE '%.css' THEN 'CSS'
                        WHEN file_path LIKE '%.json' THEN 'JSON'
                        WHEN file_path LIKE '%.yaml' OR file_path LIKE '%.yml' THEN 'YAML'
                        WHEN file_path LIKE '%.txt' THEN 'Text'
                        WHEN file_path LIKE '%.log' THEN 'Log'
                        WHEN file_path LIKE '%.md' THEN 'Markdown'
                        WHEN file_path LIKE '%.conf' OR file_path LIKE '%.config' THEN 'Config'
                        ELSE 'Diğer'
                    END as category,
                    COUNT(*) as count
                FROM monitored_files
                GROUP BY category
                ORDER BY count DESC
            """)
            
            rows = cursor.fetchall()
            return {row[0]: row[1] for row in rows}
            
        except Exception as e:
            logger.error(f"Failed to get file categories: {e}")
            return {}
        
    def get_event_statistics(self) -> Dict[str, Any]:
        """Get comprehensive event statistics"""
        try:
            cursor = self.connection.cursor()
            
            # Get events by type
            cursor.execute("""
                SELECT event_type, COUNT(*) as count
                FROM change_log
                GROUP BY event_type
                ORDER BY count DESC
            """)
            events_by_type = dict(cursor.fetchall())
            
            # Get recent events (last 24 hours)
            yesterday = datetime.now().timestamp() - (24 * 60 * 60)
            cursor.execute("""
                SELECT event_type, COUNT(*) as count
                FROM change_log
                WHERE event_time > ?
                GROUP BY event_type
            """, (yesterday,))
            recent_events_by_type = dict(cursor.fetchall())
            
            # Get events by day (last 7 days)
            week_ago = datetime.now().timestamp() - (7 * 24 * 60 * 60)
            cursor.execute("""
                SELECT date(event_time, 'unixepoch') as event_date, 
                       COUNT(*) as count
                FROM change_log
                WHERE event_time > ?
                GROUP BY event_date
                ORDER BY event_date DESC
            """, (week_ago,))
            events_by_day = dict(cursor.fetchall())
            
            return {
                "total_events": sum(events_by_type.values()),
                "events_by_type": events_by_type,
                "recent_events_by_type": recent_events_by_type,
                "events_by_day": events_by_day
            }
            
        except Exception as e:
            logger.error(f"Failed to get event statistics: {e}")
            return {}

    def get_files_with_details(self) -> List[Dict[str, Any]]:
        """Get list of all monitored files with additional details"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT mf.*, 
                       COUNT(cl.id) as event_count,
                       MAX(cl.event_time) as last_event_time,
                       datetime(mf.created_at, 'unixepoch') as created_formatted,
                       datetime(mf.updated_at, 'unixepoch') as updated_formatted
                FROM monitored_files mf
                LEFT JOIN change_log cl ON mf.id = cl.monitored_file_id
                GROUP BY mf.id
                ORDER BY mf.file_path
            """)
            
            rows = cursor.fetchall()
            files = []
            
            for row in rows:
                file_dict = dict(row)
                
                # Format timestamps
                if file_dict.get('last_scanned_time'):
                    file_dict['last_scanned'] = datetime.fromtimestamp(file_dict['last_scanned_time']).strftime('%Y-%m-%d %H:%M:%S')
                else:
                    file_dict['last_scanned'] = 'Never'
                
                if file_dict.get('last_event_time'):
                    file_dict['last_event'] = datetime.fromtimestamp(file_dict['last_event_time']).strftime('%Y-%m-%d %H:%M:%S')
                else:
                    file_dict['last_event'] = 'Never'
                
                # Format file size
                size = file_dict.get('baseline_size', 0)
                if size > 1024*1024:
                    file_dict['size_formatted'] = f"{size/(1024*1024):.1f} MB"
                elif size > 1024:
                    file_dict['size_formatted'] = f"{size/1024:.1f} KB"
                else:
                    file_dict['size_formatted'] = f"{size} B"
                
                # Extract filename and directory
                file_path = file_dict['file_path']
                file_dict['filename'] = os.path.basename(file_path)
                file_dict['directory'] = os.path.dirname(file_path)
                
                files.append(file_dict)
            
            return files
            
        except Exception as e:
            logger.error(f"Failed to get files with details: {e}")
            return []
        

# Legacy function for backward compatibility
def setup_database_and_tables():
    """
    Legacy function for setting up database tables
    This is kept for backward compatibility with existing code
    """
    try:
        # Use the same config path as before
        script_dir = Path(__file__).parent
        config_path = script_dir / "database_config.json"
        
        # Create DatabaseManager instance and connect
        db_manager = DatabaseManager(str(config_path))
        db_manager.connect()
        db_manager.disconnect()
        
        logger.info("✓ Database and tables were successfully created/verified.")
        return True
        
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        return False


# --- To run this script directly ---
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    logger.info("FIM Database Setup Script Initialized...")
    success = setup_database_and_tables()
    if success:
        logger.info("Setup completed successfully.")
    else:
        logger.error("Setup failed. Please check the errors above.")