# FIM System API Documentation

## Overview

The FIM (File Integrity Monitoring) API provides endpoints for monitoring file system changes, managing configurations, and retrieving system status.

## Base URL

- Development: `http://localhost:8000`
- Production: `http://localhost:8000`

## Authentication

Currently, no authentication is required for API access.

## Endpoints

### Health Check

**GET** `/health`

Returns the health status of the API service.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-19T12:00:00Z",
  "version": "1.0.0"
}
```

### System Status

**GET** `/api/system/status`

Returns comprehensive system status including monitoring state and database connectivity.

**Response:**
```json
{
  "monitoring_active": true,
  "database_connected": true,
  "last_scan": "2025-01-19T11:45:00Z",
  "monitored_paths": ["/app/data/test_monitoring", "/app/logs"],
  "active_profile": "balanced"
}
```

### File Status

**GET** `/api/files/status`

Returns the status of all monitored files.

**Response:**
```json
{
  "files": [
    {
      "path": "/app/data/test_monitoring/file1.txt",
      "status": "UNCHANGED",
      "last_modified": "2025-01-19T10:30:00Z",
      "hash": "abc123def456",
      "size": 1024
    }
  ],
  "total_files": 1,
  "changed_files": 0
}
```

### Manual Scan

**POST** `/api/scan/manual`

Triggers a manual file system scan.

**Request Body:**
```json
{
  "paths": ["/app/data", "/app/logs"],
  "force_rescan": false
}
```

**Response:**
```json
{
  "scan_id": "scan-123456",
  "status": "started",
  "timestamp": "2025-01-19T12:00:00Z"
}
```

### Events

**GET** `/api/events`

Returns recent file system events.

**Query Parameters:**
- `limit` (optional): Number of events to return (default: 100)
- `since` (optional): ISO 8601 timestamp to filter events from

**Response:**
```json
{
  "events": [
    {
      "id": 1,
      "file_path": "/app/data/test_monitoring/file1.txt",
      "event_type": "MODIFIED",
      "timestamp": "2025-01-19T11:45:00Z",
      "details": {
        "old_hash": "abc123",
        "new_hash": "def456",
        "size_change": 100
      }
    }
  ],
  "total": 1
}
```

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "error": "Invalid request parameters",
  "message": "Detailed error description"
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal server error",
  "message": "An unexpected error occurred"
}
```

## Interactive Documentation

Visit `/docs` for Swagger UI documentation or `/redoc` for ReDoc documentation when the API is running.
