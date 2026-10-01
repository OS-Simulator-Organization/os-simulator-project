from typing import Dict, List, Any, Optional
from src.core.base_manager import BaseManager
from src.core.events import EventRecord


class SimulationController:
    """
    Central Discrete-Event Engine maintaining simulation clock, global run state,
    and event synchronization across all manager modules.
    """

    def __init__(self, seed: int = 42):
        self.clock: float = 0.0
        self.seed: int = seed
        self.is_running: bool = False
        self.managers: Dict[str, BaseManager] = {}
        self.global_event_log: List[EventRecord] = []

    def register_manager(self, manager: BaseManager) -> None:
        """Registers an OS Manager module adhering to the BaseManager interface."""
        self.managers[manager.name] = manager

    def get_manager(self, name: str) -> Optional[BaseManager]:
        """Retrieves a registered manager instance by name."""
        return self.managers.get(name)

    def configure_all(self, configs: Dict[str, Dict[str, Any]]) -> None:
        """Configures all registered managers using a mapped configuration dictionary."""
        for manager_name, config in configs.items():
            if manager_name in self.managers:
                self.managers[manager_name].configure(config)

    def step(self) -> List[EventRecord]:
        """
        Advances simulation clock by 1 tick and executes step() across all registered managers.
        Gathers and returns all newly generated EventRecords.
        """
        step_events: List[EventRecord] = []
        
        # Step through each manager deterministically
        for manager in self.managers.values():
            new_events = manager.step(self.clock)
            step_events.extend(new_events)

        # Store in global event log and advance clock
        self.global_event_log.extend(step_events)
        self.clock += 1.0
        return step_events

    def run(self, max_ticks: int = 100) -> List[EventRecord]:
        """Runs the simulation continuously until a max tick limit or condition is met."""
        self.is_running = True
        all_run_events: List[EventRecord] = []
        
        ticks = 0
        while self.is_running and ticks < max_ticks:
            events = self.step()
            all_run_events.extend(events)
            ticks += 1

        self.is_running = False
        return all_run_events

    def reset(self) -> None:
        """Resets the simulation engine clock and all registered manager states."""
        self.clock = 0.0
        self.is_running = False
        self.global_event_log.clear()
        for manager in self.managers.values():
            manager.reset()

    def get_system_snapshot(self) -> Dict[str, Any]:
        """Compiles a complete snapshot of all managers for dashboard updates."""
        return {
            "clock": self.clock,
            "managers": {
                name: manager.snapshot() for name, manager in self.managers.items()
            }
        }

    def get_system_metrics(self) -> Dict[str, Any]:
        """Gathers runtime metrics across all managers for analytics and export."""
        return {
            name: manager.metrics() for name, manager in self.managers.items()
        }