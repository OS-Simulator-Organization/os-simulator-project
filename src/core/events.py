import json
import os
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any
import jsonschema

# Resolve path to docs/event_schema.json relative to src/core/events.py
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCHEMA_PATH = os.path.join(BASE_DIR, "docs", "event_schema.json")

def load_event_schema() -> Dict[str, Any]:
    """Loads the JSON schema definition for event validation."""
    if not os.path.exists(SCHEMA_PATH):
        raise FileNotFoundError(f"Event schema not found at expected location: {SCHEMA_PATH}")
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

_EVENT_COUNTER = 0  # Global counter for tie-breaking in EventRecord

@dataclass(order=True)
class EventRecord:
    timestamp: float #priority key for sorting events
    _seq: int = field(init=False)  # Secondary tie-breaking key
    manager: str = field(compare=False)
    event_type: str = field(compare=False)
    entity_id: str = field(compare=False)
    action: str = field(compare=False)
    previous_state: str = field(compare=False)
    new_state: str = field(compare=False)
    outcome: str = field(compare=False)
    duration_or_cost: float = field(default=0.0, compare=False)
    explanatory_message: str = field(default="", compare=False) 
    correlation_id: Optional[str] = field(default=None, compare=False) #relates to a specific request or transaction, useful for tracing events across systems
    
    
    def __post_init__(self):
        global _EVENT_COUNTER
        _EVENT_COUNTER += 1
        self._seq = _EVENT_COUNTER

    def to_dict(self) -> Dict[str, Any]:
        """Converts the event to a dictionary for JSON serialization and UI logs."""
        data = asdict(self)
        #Exclude the internal sequence number from the dictionary representation
        data.pop('_seq', None)
        return data


# The following methods are added to the EventRecord class for validation and creation from a dictionary.
    def validate(self) -> bool:
        """Validates this record instance against the event_schema.json."""
        schema = load_event_schema()
        jsonschema.validate(instance=self.to_dict(), schema=schema)
        return True


# The following class method is added to the EventRecord class for creating an instance from a dictionary.
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EventRecord":
        """Creates and validates an EventRecord from a dictionary."""
        schema = load_event_schema()
        jsonschema.validate(instance=data, schema=schema)
        return cls(**data)
