"""
FIM (File Integrity Monitor) API Service
FastAPI-based backend for file integrity monitoring system
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Add the parent directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import DatabaseManager
from settings.config_loader import ConfigLoader
from core.monitor import FileMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/fim_api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# FastAPI app instance
app = FastAPI(
    title="FIM API Service",
    description="File Integrity Monitoring API for tracking file changes",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
db_manager = None
config_loader = None
file_monitor = None

# Pydantic models for API requests/responses
class FileStatusResponse(BaseModel):
    file_path: str
    status: str
    last_modified: Optional[str]
    checksum: Optional[str]

class SystemStatusResponse(BaseModel):
    status: str
    uptime: str
    monitored_files: int
    events_count: int
    last_scan: Optional[str]

class ScanRequest(BaseModel):
    paths: Optional[List[str]] = None
    force_rescan: bool = False

@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup"""
    global db_manager, config_loader, file_monitor
    
    logger.info("Starting FIM API Service...")
    
    try:
        # Load configuration
        config_path = "/app/config.yaml"
        config_loader = ConfigLoader()
        config = config_loader.load_config(config_path)
        logger.info(f"Configuration loaded from: {config_path}")
        
        # Initialize database
        db_config_path = "/app/fim_scanner/database/database_config.json"
        db_manager = DatabaseManager(db_config_path)
        db_manager.connect()
        logger.info("Database connection established")
        
        # Initialize file monitor
        file_monitor = FileMonitor(config, db_manager)
        logger.info("File monitor initialized")
        
        # Initialize baseline if needed
        from database.initialize_baseline import initialize_baseline
        initialize_baseline(db_manager, config.get('paths_to_monitor', []))
        logger.info("Baseline initialization completed")
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    global db_manager
    
    logger.info("Shutting down FIM API Service...")
    if db_manager:
        db_manager.disconnect()
    logger.info("Shutdown completed")

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "FIM API Service", "version": "1.0.0", "status": "running"}

@app.get("/api/v1/file-details/{file_id}")
async def get_file_details_by_id(file_id: int):
    """Get detailed information about a file by its ID"""
    try:
        if not db_manager:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
        cursor = db_manager.connection.cursor()
        cursor.execute("""
            SELECT * FROM monitored_files WHERE id = ?
        """, (file_id,))
        
        file_row = cursor.fetchone()
        if not file_row:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_info = dict(file_row)
        
        # Get file events
        cursor.execute("""
            SELECT *, datetime(event_time, 'unixepoch') as formatted_time
            FROM change_log 
            WHERE monitored_file_id = ? OR file_path = ?
            ORDER BY event_time DESC 
            LIMIT 50
        """, (file_id, file_info['file_path']))
        
        events = [dict(row) for row in cursor.fetchall()]
        
        return {
            "file_info": file_info,
            "recent_events": events,
            "total_events": len(events)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get file details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug-test")
async def debug_test():
    """Simple debug test endpoint"""
    logger.error("DEBUG: debug_test endpoint called")
    return {"debug": "test endpoint working", "timestamp": datetime.now().isoformat()}

@app.get("/health")
async def health_check():
    """Health check endpoint for Docker"""
    logger.error("DEBUG: health_check called - this should appear in logs")
    try:
        # Check database connection
        if db_manager and db_manager.connection:
            db_status = "connected"
        else:
            db_status = "disconnected"
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": db_status,
            "service": "fim-api"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.get("/api/v1/status")
async def get_system_status():
    """Get overall system status"""
    try:
        if not db_manager:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
        # Get statistics from database
        events_count = db_manager.get_events_count()
        monitored_files_count = db_manager.get_monitored_files_count()
        last_scan = db_manager.get_last_scan_time()
        
        return {
            "status": "running",
            "uptime": str(datetime.now()),
            "monitored_files_count": monitored_files_count,
            "events_count": events_count,
            "last_scan": last_scan,
            "active_profile": "Default Security Profile"
        }
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/files")
async def get_monitored_files():
    """Get list of all monitored files"""
    try:
        if not db_manager:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
        files = db_manager.get_all_files()
        return {"files": files, "count": len(files)}
    except Exception as e:
        logger.error(f"Failed to get monitored files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/events")
async def get_events(limit: int = 100, offset: int = 0):
    """Get recent events"""
    try:
        if not db_manager:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
        events = db_manager.get_events(limit=limit, offset=offset)
        total = db_manager.get_events_count()
        return {"events": events, "count": len(events), "total": total}
    except Exception as e:
        logger.error(f"Failed to get events: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/scan")
async def trigger_scan(scan_request: ScanRequest, background_tasks: BackgroundTasks):
    """Trigger a manual scan"""
    try:
        if not file_monitor:
            raise HTTPException(status_code=503, detail="File monitor not initialized")
        
        # Add scan task to background
        background_tasks.add_task(
            perform_scan, 
            scan_request.paths, 
            scan_request.force_rescan
        )
        
        return {
            "message": "Scan initiated",
            "timestamp": datetime.now().isoformat(),
            "paths": scan_request.paths,
            "force_rescan": scan_request.force_rescan
        }
    except Exception as e:
        logger.error(f"Failed to trigger scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/files/detailed")
async def get_files_detailed():
    """Get list of all monitored files with detailed information"""
    try:
        if not db_manager:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
        files = db_manager.get_files_with_details()
        return {"files": files, "count": len(files)}
    except Exception as e:
        logger.error(f"Failed to get detailed files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/debug/{file_path:path}")
async def debug_path(file_path: str):
    """Debug endpoint to test path parsing"""
    result = {
        "file_path": file_path,
        "endswith_details": file_path.endswith('/details'),
    }
    
    if file_path.endswith('/details'):
        potential_id = file_path[:-8]
        result["potential_id"] = potential_id
        try:
            file_id = int(potential_id)
            result["parsed_id"] = file_id
            result["is_valid_int"] = True
        except ValueError:
            result["is_valid_int"] = False
    
    return result

@app.get("/api/v1/files/{file_path:path}")
async def get_file_status(file_path: str):
    """Get status of a specific file or file details if path ends with /details"""
    print(f"DEBUG: get_file_status called with file_path='{file_path}'")
    try:
        if not db_manager:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
        # Debug logging
        logger.info(f"Received request for file_path: '{file_path}'")
        logger.info(f"Ends with /details: {file_path.endswith('/details')}")
        
        # Check if this is actually a request for file details by ID
        if file_path.endswith('/details'):
            # Extract the potential file_id
            potential_id = file_path[:-8]  # Remove '/details'
            logger.info(f"Potential ID: '{potential_id}'")
            try:
                file_id = int(potential_id)
                logger.info(f"Successfully parsed ID: {file_id}")
                # This is a file details request by ID, handle it here
                cursor = db_manager.connection.cursor()
                cursor.execute("""
                    SELECT * FROM monitored_files WHERE id = ?
                """, (file_id,))
                
                file_row = cursor.fetchone()
                logger.info(f"Database query result: {file_row is not None}")
                if not file_row:
                    raise HTTPException(status_code=404, detail="File not found")
                
                file_info = dict(file_row)
                
                # Get file events
                cursor.execute("""
                    SELECT *, datetime(event_time, 'unixepoch') as formatted_time
                    FROM change_log 
                    WHERE monitored_file_id = ? OR file_path = ?
                    ORDER BY event_time DESC 
                    LIMIT 50
                """, (file_id, file_info['file_path']))
                
                events = [dict(row) for row in cursor.fetchall()]
                
                return {
                    "file_info": file_info,
                    "recent_events": events,
                    "total_events": len(events)
                }
            except ValueError as e:
                logger.info(f"Failed to parse as integer: {e}")
                # Not a valid integer, this means it's a file path that ends with /details
                # So we should look for a file literally named "something/details"
                pass
        
        # Regular file status request
        logger.info(f"Processing as regular file path: '{file_path}'")
        file_info = db_manager.get_file_info(file_path)
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found in monitoring database")
        
        return FileStatusResponse(
            file_path=file_path,
            status=file_info.get('status', 'unknown'),
            last_modified=file_info.get('last_modified'),
            checksum=file_info.get('checksum')
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get file status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/events/formatted")
async def get_events_formatted(limit: int = 50):
    """Get recent events with formatted data"""
    try:
        if not db_manager:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
        events = db_manager.get_recent_events_formatted(limit=limit)
        return {"events": events, "count": len(events)}
    except Exception as e:
        logger.error(f"Failed to get formatted events: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/statistics")
async def get_statistics():
    """Get detailed statistics for dashboard"""
    try:
        if not db_manager:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
        # Get file categories
        categories = db_manager.get_file_categories()
        
        # Get recent activity (last 24 hours)
        cursor = db_manager.connection.cursor()
        yesterday = datetime.now().timestamp() - (24 * 60 * 60)
        cursor.execute("""
            SELECT COUNT(*) FROM change_log 
            WHERE event_time > ?
        """, (yesterday,))
        recent_activity = cursor.fetchone()[0]
        
        # Get critical events count
        cursor.execute("""
            SELECT COUNT(*) FROM change_log 
            WHERE event_type IN ('deleted', 'modified')
            AND event_time > ?
        """, (yesterday,))
        critical_events = cursor.fetchone()[0]
        
        return {
            "file_categories": categories,
            "recent_activity_24h": recent_activity,
            "critical_events_24h": critical_events,
            "total_files": db_manager.get_monitored_files_count(),
            "total_events": db_manager.get_events_count()
        }
        
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/statistics/detailed")
async def get_detailed_statistics():
    """Get comprehensive statistics including event details"""
    try:
        if not db_manager:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
        # Get basic statistics
        categories = db_manager.get_file_categories()
        event_stats = db_manager.get_event_statistics()
        
        # Get recent activity (last 24 hours)
        cursor = db_manager.connection.cursor()
        yesterday = datetime.now().timestamp() - (24 * 60 * 60)
        cursor.execute("""
            SELECT COUNT(*) FROM change_log 
            WHERE event_time > ?
        """, (yesterday,))
        recent_activity = cursor.fetchone()[0]
        
        # Get critical events count
        cursor.execute("""
            SELECT COUNT(*) FROM change_log 
            WHERE event_type IN ('deleted', 'modified')
            AND event_time > ?
        """, (yesterday,))
        critical_events = cursor.fetchone()[0]
        
        return {
            "file_categories": categories,
            "recent_activity_24h": recent_activity,
            "critical_events_24h": critical_events,
            "total_files": db_manager.get_monitored_files_count(),
            "total_events": db_manager.get_events_count(),
            "event_statistics": event_stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get detailed statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/files/config.json")
async def get_config_file_details():
    """Get detailed information about config.json file specifically"""
    try:
        if not db_manager:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
        # Find config.json file in the database
        cursor = db_manager.connection.cursor()
        cursor.execute("""
            SELECT * FROM monitored_files WHERE file_path LIKE '%config.json%'
        """)
        
        file_row = cursor.fetchone()
        if not file_row:
            raise HTTPException(status_code=404, detail="config.json file not found in monitoring database")
        
        file_info = dict(file_row)
        file_id = file_info['id']
        
        # Get file events
        cursor.execute("""
            SELECT *, datetime(event_time, 'unixepoch') as formatted_time
            FROM change_log 
            WHERE monitored_file_id = ? OR file_path = ?
            ORDER BY event_time DESC 
            LIMIT 50
        """, (file_id, file_info['file_path']))
        
        events = [dict(row) for row in cursor.fetchall()]
        
        # Format event details
        for event in events:
            event_time = datetime.fromtimestamp(event['event_time'])
            time_diff = datetime.now() - event_time
            
            if time_diff.days > 0:
                event['time_ago'] = f"{time_diff.days} days ago"
            elif time_diff.seconds > 3600:
                hours = time_diff.seconds // 3600
                event['time_ago'] = f"{hours} hours ago"
            elif time_diff.seconds > 60:
                minutes = time_diff.seconds // 60
                event['time_ago'] = f"{minutes} minutes ago"
            else:
                event['time_ago'] = "Just now"
        
        # Format file info
        if file_info.get('last_scanned_time'):
            file_info['last_scanned_formatted'] = datetime.fromtimestamp(file_info['last_scanned_time']).strftime('%Y-%m-%d %H:%M:%S')
        
        if file_info.get('baseline_creation_time'):
            file_info['created_formatted'] = datetime.fromtimestamp(file_info['baseline_creation_time']).strftime('%Y-%m-%d %H:%M:%S')
        
        # Format file size
        size = file_info.get('baseline_size', 0)
        if size > 1024*1024:
            file_info['size_formatted'] = f"{size/(1024*1024):.1f} MB"
        elif size > 1024:
            file_info['size_formatted'] = f"{size/1024:.1f} KB"
        else:
            file_info['size_formatted'] = f"{size} B"
        
        return {
            "file": file_info,
            "events": events,
            "events_count": len(events)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get config.json file details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/files/by-path")
async def get_file_by_path(path: str):
    """Get file information by path"""
    try:
        if not db_manager:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
        cursor = db_manager.connection.cursor()
        cursor.execute("""
            SELECT id FROM monitored_files WHERE file_path = ?
        """, (path,))
        
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="File not found")
        
        return {"file_id": result[0]}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get file by path: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def perform_scan(paths: Optional[List[str]] = None, force_rescan: bool = False):
    """Background task to perform file scan"""
    try:
        logger.info(f"Starting background scan - paths: {paths}, force_rescan: {force_rescan}")
        
        if file_monitor:
            if paths:
                for path in paths:
                    file_monitor.scan_path(path, force_rescan)
            else:
                file_monitor.scan_all_paths(force_rescan)
            
            logger.info("Background scan completed successfully")
        else:
            logger.error("File monitor not available for background scan")
    except Exception as e:
        logger.error(f"Background scan failed: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
