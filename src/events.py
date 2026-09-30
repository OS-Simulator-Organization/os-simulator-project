# src/events.py
import json
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, Any, Optional


class ManagerType(Enum):
    PROCESS = "PROCESS_MANAGER"
    MEMORY = "MEMORY_MANAGER"
    FILE_SYSTEM = "FILE_SYSTEM_MANAGER"
    SECURITY = "SECURITY_MANAGER"
    DEVICE = "DEVICE_MANAGER"
    NETWORK = "NETWORK_MANAGER"
    SYSTEM = "SIMULATION_ENGINE"


@dataclass
class EventRecord:
    timestamp: int                  
    manager: str                    # Subsystem producing event (e.g., "PROCESS_MANAGER")
    event_type: str                 
    entity_id: str                  # Associated Data Model ID (e.g., PID, Frame ID, Path)
    action: str                     
    outcome: str                    
    
    # Optional metadata
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    details: Dict[str, Any] = field(default_factory=dict) # Contextual metadata payload

    def to_dict(self) -> Dict[str, Any]:
        """Converts EventRecord instance into a standard dictionary."""
        data = asdict(self)
        if isinstance(self.manager, Enum):
            data["manager"] = self.manager.value
        return data

    def to_json(self) -> str:
        """Serializes EventRecord into a standard JSON string for file logging."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EventRecord':
        """Instantiates an EventRecord from a dictionary."""
        return cls(**data)