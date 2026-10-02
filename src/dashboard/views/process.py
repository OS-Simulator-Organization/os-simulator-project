from src.core.controller_api import RunConfig
from src.dashboard.manager_view import ManagerView


def describe_config(config: RunConfig) -> str:
    process = config.process
    quantum = f"{process.quantum_ms} ms" if process.quantum_ms is not None else "–"
    return f"Policy: {process.policy.value} · Quantum: {quantum} · Context switch: {process.context_switch_ms} ms"


VIEW = ManagerView(
    name="Process",
    manager="Process",
    regions=("CPU Gantt chart", "Process table"),
    actions=("Run process tests",),
    describe_config=describe_config,
)
