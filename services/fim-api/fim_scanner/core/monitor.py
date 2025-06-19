"""
File Integrity Monitor Core Module
Handles file system monitoring and integrity checking
"""

import os
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

try:
    from models.event_model import EventType, FileEvent
except ImportError:
    # Fallback if event model is not available
    class EventType:
        CREATED = "created"
        MODIFIED = "modified"
        DELETED = "deleted"
        MOVED = "moved"
        RENAMED = "renamed"
        ACCESSED = "accessed"
    
    class FileEvent:
        def __init__(self, event_type, file_path, **kwargs):
            self.event_type = event_type
            self.file_path = file_path
            for k, v in kwargs.items():
                setattr(self, k, v)

logger = logging.getLogger(__name__)

class FIMEventHandler(FileSystemEventHandler):
    """Custom event handler for file system events"""
    
    def __init__(self, monitor_instance):
        super().__init__()
        self.monitor = monitor_instance
    
    def on_modified(self, event: FileSystemEvent):
        """Handle file modification events"""
        if not event.is_directory:
            self.monitor.handle_file_change(event.src_path, 'modified')
    
    def on_created(self, event: FileSystemEvent):
        """Handle file creation events"""
        if not event.is_directory:
            self.monitor.handle_file_change(event.src_path, 'created')
    
    def on_deleted(self, event: FileSystemEvent):
        """Handle file deletion events"""
        if not event.is_directory:
            self.monitor.handle_file_change(event.src_path, 'deleted')
    
    def on_moved(self, event: FileSystemEvent):
        """Handle file move/rename events"""
        if not event.is_directory:
            # Handle the old file as deleted
            self.monitor.handle_file_change(event.src_path, 'deleted')
            # Handle the new file as moved/created
            self.monitor.handle_file_change(event.dest_path, 'moved')
            
            # If it's just a rename (same directory), mark as renamed
            src_dir = os.path.dirname(event.src_path)
            dest_dir = os.path.dirname(event.dest_path)
            if src_dir == dest_dir:
                self.monitor.handle_file_change(event.dest_path, 'renamed')

class FileMonitor:
    """Main file monitoring class for FIM system"""
    
    def __init__(self, config: Dict[str, Any], db_manager):
        """
        Initialize the file monitor
        
        Args:
            config: Configuration dictionary
            db_manager: Database manager instance
        """
        self.config = config
        self.db_manager = db_manager
        self.observer = Observer()
        self.monitoring_paths = config.get('paths_to_monitor', [])
        self.excluded_patterns = config.get('excluded_patterns', [])
        self.is_monitoring = False
        
        logger.info(f"FileMonitor initialized with {len(self.monitoring_paths)} paths")
    
    def calculate_file_hash(self, file_path: str) -> Optional[str]:
        """Calculate SHA256 hash of a file"""
        try:
            with open(file_path, 'rb') as f:
                sha256_hash = hashlib.sha256()
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
                return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate hash for {file_path}: {e}")
            return None
    
    def should_monitor_file(self, file_path: str) -> bool:
        """Check if file should be monitored based on exclusion patterns"""
        file_path = str(file_path)
        
        # Check exclusion patterns
        for pattern in self.excluded_patterns:
            if pattern in file_path:
                return False
        
        # Skip common system files and directories
        skip_patterns = ['.git', '__pycache__', '.pyc', '.tmp', '.log']
        for pattern in skip_patterns:
            if pattern in file_path:
                return False
        
        return True
    
    def handle_file_change(self, file_path: str, event_type: str):
        """Handle file system change events"""
        try:
            if not self.should_monitor_file(file_path):
                return
            
            logger.info(f"File {event_type}: {file_path}")
            
            # Calculate new hash if file exists
            new_hash = None
            file_size = 0
            if event_type != 'deleted' and os.path.exists(file_path):
                new_hash = self.calculate_file_hash(file_path)
                file_size = os.path.getsize(file_path)
            
            # Get existing file info from database
            existing_info = self.db_manager.get_file_info(file_path)
            
            # Only record event if there's an actual change
            should_record_event = False
            old_hash = existing_info.get('baseline_hash') if existing_info else None
            
            if event_type == 'deleted':
                should_record_event = True
            elif event_type == 'created':
                should_record_event = existing_info is None  # Only if truly new
            elif event_type == 'modified':
                # Only record if hash actually changed
                should_record_event = old_hash != new_hash
            else:  # moved
                should_record_event = True
            
            if should_record_event:
                # Record the event
                self.db_manager.record_event({
                    'file_path': file_path,
                    'event_type': event_type,
                    'timestamp': datetime.now().isoformat(),
                    'old_hash': old_hash,
                    'new_hash': new_hash,
                    'file_size': file_size,
                    'description': f"File {event_type}: {os.path.basename(file_path)}"
                })
                logger.info(f"Recorded change event for {file_path}: {event_type}")
            else:
                logger.debug(f"No actual change detected for {file_path}, skipping event")
            
            # Update file info in database
            if event_type != 'deleted':
                self.db_manager.update_file_info(file_path, new_hash, file_size)
            else:
                self.db_manager.remove_file_info(file_path)
                
        except Exception as e:
            logger.error(f"Error handling file change {file_path}: {e}")
    
    def scan_path(self, path: str, force_rescan: bool = False):
        """Scan a specific path for files and update baseline"""
        try:
            path_obj = Path(path)
            if not path_obj.exists():
                logger.warning(f"Path does not exist: {path}")
                return
            
            logger.info(f"Scanning path: {path}")
            scanned_count = 0
            
            if path_obj.is_file():
                # Single file
                if self.should_monitor_file(str(path_obj)):
                    self._process_file(path_obj, force_rescan)
                    scanned_count = 1
            else:
                # Directory - scan recursively
                for file_path in path_obj.rglob('*'):
                    if file_path.is_file() and self.should_monitor_file(str(file_path)):
                        self._process_file(file_path, force_rescan)
                        scanned_count += 1
            
            logger.info(f"Scanned {scanned_count} files in {path}")
            
        except Exception as e:
            logger.error(f"Error scanning path {path}: {e}")
    
    def scan_all_paths(self, force_rescan: bool = False):
        """Scan all configured monitoring paths"""
        logger.info("Starting full system scan...")
        
        for path in self.monitoring_paths:
            self.scan_path(path, force_rescan)
        
        logger.info("Full system scan completed")
    
    def _process_file(self, file_path: Path, force_rescan: bool = False):
        """Process a single file for monitoring"""
        try:
            file_str = str(file_path)
            current_hash = self.calculate_file_hash(file_str)
            
            if current_hash is None:
                return
            
            # Check if file is already in database
            existing_info = self.db_manager.get_file_info(file_str)
            
            if not existing_info:
                # New file - add to monitoring
                file_size = os.path.getsize(file_str)
                self.db_manager.update_file_info(file_str, current_hash, file_size)
                logger.debug(f"Added new file to monitoring: {file_str}")
            elif force_rescan:
                # Forced rescan - update baseline
                file_size = os.path.getsize(file_str)
                self.db_manager.update_file_info(file_str, current_hash, file_size)
                logger.debug(f"Updated baseline for: {file_str}")
            else:
                # Check if file has actually changed
                stored_hash = existing_info.get('baseline_hash')
                if stored_hash != current_hash:
                    logger.warning(f"File integrity changed: {file_str}")
                    # This will trigger a proper change detection
                    self.handle_file_change(file_str, 'modified')
                else:
                    # File hasn't changed, just update scan time
                    current_time = datetime.now().timestamp()
                    try:
                        cursor = self.db_manager.connection.cursor()
                        cursor.execute("""
                            UPDATE monitored_files 
                            SET last_scanned_time = ?, updated_at = ?
                            WHERE file_path = ?
                        """, (current_time, current_time, file_str))
                        self.db_manager.connection.commit()
                    except Exception as e:
                        logger.error(f"Failed to update scan time for {file_str}: {e}")
                    
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
    
    def start_monitoring(self):
        """Start real-time file system monitoring"""
        try:
            if self.is_monitoring:
                logger.warning("Monitoring is already active")
                return
            
            # Set up file system watchers
            event_handler = FIMEventHandler(self)
            
            for path in self.monitoring_paths:
                if os.path.exists(path):
                    self.observer.schedule(event_handler, path, recursive=True)
                    logger.info(f"Watching path: {path}")
                else:
                    logger.warning(f"Monitoring path does not exist: {path}")
            
            self.observer.start()
            self.is_monitoring = True
            logger.info("Real-time monitoring started")
            
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            raise
    
    def stop_monitoring(self):
        """Stop real-time file system monitoring"""
        try:
            if self.observer.is_alive():
                self.observer.stop()
                self.observer.join()
            
            self.is_monitoring = False
            logger.info("Real-time monitoring stopped")
            
        except Exception as e:
            logger.error(f"Error stopping monitoring: {e}")
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status"""
        return {
            'is_monitoring': self.is_monitoring,
            'paths_count': len(self.monitoring_paths),
            'observer_alive': self.observer.is_alive() if self.observer else False,
            'monitored_paths': self.monitoring_paths
        }
