from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

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