from abc import ABC, abstractmethod
from typing import Any, Dict, List
from src.events import EventRecord

class BaseManager(ABC):
    """
    Abstract Base Class enforcing the mandatory Manager API Contract (Appendix A).
    All OS managers and the parallel engine must inherit from this class.
    """

    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> None:
        """Validate and apply manager-specific configuration (e.g., page size, quantum)."""
        pass

    @abstractmethod
    def load(self, input_data: Any) -> None:
        """Import a workload or scenario asset without mutating unrelated managers."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Return the manager to a known initial state."""
        pass

    @abstractmethod
    def step(self, current_time: float) -> List[EventRecord]:
        """
        Advance deterministically by one step/tick and return 
        zero or more shared EventRecords generated during execution.
        """
        pass

    @abstractmethod
    def run(self, stop_condition: Any = None) -> List[EventRecord]:
        """Advance execution until completion or a requested limit/condition is reached."""
        pass

    @abstractmethod
    def snapshot(self) -> Dict[str, Any]:
        """Return a serializable dictionary representing current internal state for UI rendering."""
        pass

    @abstractmethod
    def metrics(self) -> Dict[str, Any]:
        """Return defined operational measurements with standard units (e.g., hit rate, turnaround time)."""
        pass

    @abstractmethod
    def validate(self) -> List[str]:
        """Validate internal configuration and state; return a list of error or warning strings."""
        pass

    @abstractmethod
    def export(self, export_format: str = "json") -> Any:
        """Produce results, event metrics, and state data in an approved format (e.g., JSON, CSV)."""
        pass
