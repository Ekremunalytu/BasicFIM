#!/usr/bin/env python3
"""
Event model for FIM system
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

class EventType(Enum):
    """File system event types"""
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"
    RENAMED = "renamed"
    ACCESSED = "accessed"

@dataclass
class FileEvent:
    """File system event data structure"""
    event_type: EventType
    file_path: str
    monitored_file_id: Optional[int] = None
    event_time: Optional[float] = None
    old_hash: Optional[str] = None
    new_hash: Optional[str] = None
    file_size: Optional[int] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.event_time is None:
            self.event_time = datetime.now().timestamp()
        
        if isinstance(self.event_type, str):
            self.event_type = EventType(self.event_type)
        
        if self.description is None:
            self.description = self._generate_description()
    
    def _generate_description(self) -> str:
        """Generate a description based on event type"""
        descriptions = {
            EventType.CREATED: f"Dosya oluşturuldu: {self.file_path}",
            EventType.MODIFIED: f"Dosya değiştirildi: {self.file_path}",
            EventType.DELETED: f"Dosya silindi: {self.file_path}",
            EventType.MOVED: f"Dosya taşındı: {self.file_path}",
            EventType.RENAMED: f"Dosya yeniden adlandırıldı: {self.file_path}",
            EventType.ACCESSED: f"Dosyaya erişildi: {self.file_path}"
        }
        return descriptions.get(self.event_type, f"Dosya olayı: {self.file_path}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'event_type': self.event_type.value,
            'file_path': self.file_path,
            'monitored_file_id': self.monitored_file_id,
            'event_time': self.event_time,
            'old_hash': self.old_hash,
            'new_hash': self.new_hash,
            'file_size': self.file_size,
            'description': self.description,
            'metadata': self.metadata
        }

# Event type labels for UI display
EVENT_TYPE_LABELS = {
    EventType.CREATED: "📄 OLUŞTURULDU",
    EventType.MODIFIED: "✏️ DEĞİŞTİRİLDİ", 
    EventType.DELETED: "🗑️ SİLİNDİ",
    EventType.MOVED: "📁 TAŞINDI",
    EventType.RENAMED: "📝 YENİDEN ADLANDIRILDI",
    EventType.ACCESSED: "👁️ ERİŞİLDİ"
}

# Event type colors for UI
EVENT_TYPE_COLORS = {
    EventType.CREATED: "#10b981",
    EventType.MODIFIED: "#f59e0b",
    EventType.DELETED: "#ef4444", 
    EventType.MOVED: "#8b5cf6",
    EventType.RENAMED: "#06b6d4",
    EventType.ACCESSED: "#84cc16"
}
