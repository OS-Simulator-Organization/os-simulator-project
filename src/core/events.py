import json
import os
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
import jsonschema

# Resolve path to docs/events_schema.json relative to src/core/events.py
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCHEMA_PATH = os.path.join(BASE_DIR, "docs", "events_schema.json")

def load_event_schema() -> Dict[str, Any]:
    """Loads the JSON schema definition for event validation."""
    if not os.path.exists(SCHEMA_PATH):
        raise FileNotFoundError(f"Event schema not found at expected location: {SCHEMA_PATH}")
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

@dataclass
class EventRecord:
    timestamp: float
    manager: str
    event_type: str
    entity_id: str
    action: str
    previous_state: str
    new_state: str
    outcome: str
    duration_or_cost: float = 0.0
    explanatory_message: str = ""
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Converts the event to a dictionary for JSON serialization and UI logs."""
        return asdict(self)

    def validate(self) -> bool:
        """Validates this record instance against the events_schema.json."""
        schema = load_event_schema()
        jsonschema.validate(instance=self.to_dict(), schema=schema)
        return True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EventRecord":
        """Creates and validates an EventRecord from a dictionary."""
        schema = load_event_schema()
        jsonschema.validate(instance=data, schema=schema)
        return cls(**data)
