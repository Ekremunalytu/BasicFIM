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

@app.get("/health")
async def health_check():
    """Health check endpoint for Docker"""
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

@app.get("/api/v1/files/{file_path:path}")
async def get_file_status(file_path: str):
    """Get status of a specific file"""
    try:
        if not db_manager:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
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
