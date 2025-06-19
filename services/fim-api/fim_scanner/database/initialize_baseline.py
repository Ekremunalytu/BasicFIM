"""
Baseline Initialization Module for FIM System
Initializes the baseline of files to be monitored
"""

import os
import sys
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of a file"""
    try:
        with open(file_path, 'rb') as f:
            sha256_hash = hashlib.sha256()
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
    except Exception as e:
        logger.error(f"Failed to calculate hash for {file_path}: {e}")
        return ""

def should_monitor_file(file_path: str) -> bool:
    """Check if file should be monitored"""
    file_path_str = str(file_path)
    
    # Skip common patterns that shouldn't be monitored
    skip_patterns = [
        '.git', '__pycache__', '.pyc', '.tmp', '.log', 
        '.cache', '.swap', '~', '.DS_Store', 'Thumbs.db'
    ]
    
    for pattern in skip_patterns:
        if pattern in file_path_str:
            return False
    
    # Only monitor regular files
    try:
        return os.path.isfile(file_path) and not os.path.islink(file_path)
    except:
        return False

def initialize_baseline(db_manager, paths_to_monitor: List[str]):
    """
    Initialize baseline for files in specified paths
    
    Args:
        db_manager: DatabaseManager instance
        paths_to_monitor: List of paths to monitor
    """
    try:
        logger.info("Starting baseline initialization...")
        
        if not paths_to_monitor:
            logger.warning("No paths to monitor specified")
            return
        
        total_files = 0
        processed_files = 0
        
        for path_str in paths_to_monitor:
            try:
                path = Path(path_str)
                
                if not path.exists():
                    logger.warning(f"Path does not exist: {path_str}")
                    continue
                
                logger.info(f"Processing path: {path_str}")
                
                if path.is_file():
                    # Single file
                    if should_monitor_file(str(path)):
                        _process_baseline_file(db_manager, str(path))
                        processed_files += 1
                        total_files += 1
                else:
                    # Directory - scan recursively
                    for file_path in path.rglob('*'):
                        if should_monitor_file(str(file_path)):
                            total_files += 1
                            if _process_baseline_file(db_manager, str(file_path)):
                                processed_files += 1
                
            except Exception as e:
                logger.error(f"Error processing path {path_str}: {e}")
        
        logger.info(f"Baseline initialization completed: {processed_files}/{total_files} files processed")
        
    except Exception as e:
        logger.error(f"Failed to initialize baseline: {e}")
        raise

def _process_baseline_file(db_manager, file_path: str) -> bool:
    """Process a single file for baseline"""
    try:
        # Check if file already exists in database
        existing_info = db_manager.get_file_info(file_path)
        
        if existing_info:
            logger.debug(f"File already in baseline: {file_path}")
            return True
        
        # Calculate file hash
        file_hash = calculate_file_hash(file_path)
        if not file_hash:
            logger.warning(f"Could not calculate hash for: {file_path}")
            return False
        
        # Get file size
        try:
            file_size = os.path.getsize(file_path)
        except:
            file_size = 0
        
        # Add to database without recording as an event (it's baseline)
        cursor = db_manager.connection.cursor()
        current_time = datetime.now().timestamp()
        
        cursor.execute("""
            INSERT INTO monitored_files 
            (file_path, baseline_hash, baseline_size, baseline_creation_time, 
             last_scanned_time, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'OK', ?, ?)
        """, (file_path, file_hash, file_size, current_time, current_time, current_time, current_time))
        
        db_manager.connection.commit()
        logger.debug(f"Added to baseline: {file_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error processing baseline file {file_path}: {e}")
        return False

def populate_baseline_from_config():
    """
    Legacy function for backward compatibility
    This function is kept for existing code that might call it
    """
    try:
        logger.info("Legacy baseline initialization called")
        
        # Import here to avoid circular imports
        from database import DatabaseManager
        
        # Use default config path
        script_dir = Path(__file__).parent
        config_path = script_dir / "database_config.json"
        
        # Initialize database manager
        db_manager = DatabaseManager(str(config_path))
        db_manager.connect()
        
        # Default paths for legacy compatibility
        default_paths = ["/app/test_monitoring"]  # Adjust as needed
        
        # Initialize baseline
        initialize_baseline(db_manager, default_paths)
        
        db_manager.disconnect()
        
        logger.info("Legacy baseline initialization completed")
        return True
        
    except Exception as e:
        logger.error(f"Legacy baseline initialization failed: {e}")
        return False

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    success = populate_baseline_from_config()
    
    if success:
        logger.info("Baseline initialization completed successfully.")
    else:
        logger.error("Baseline initialization failed. Please check the errors above.")