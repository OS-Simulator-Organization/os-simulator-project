import json

import pytest

from src.core.controller import SimulationController
from src.core.DummyProcessManager import DummyProcessManager
from src.core.events import SCHEMA_PATH
from src.core.models import Process
from src.managers.file_manager import FileManager
from src.managers.memory_manager import MemoryManager
from src.managers.process_manager import ProcessManager


def make_controller():
    controller = SimulationController(seed=42)
    manager = DummyProcessManager()
    controller.register_manager(manager)
    manager.load([
        Process(pid="P1", owner_id="user_admin", arrival_time=0, burst_time=5, priority=1, remaining_time=5),
        Process(pid="P2", owner_id="user_guest", arrival_time=1, burst_time=3, priority=2, remaining_time=3),
    ])
    return controller


def test_processes_arrive_on_their_tick():
    controller = make_controller()

    tick_0 = controller.step()
    tick_1 = controller.step()

    assert [e.entity_id for e in tick_0] == ["P1"]
    assert [e.entity_id for e in tick_1] == ["P2"]


def test_events_match_schema():
    controller = make_controller()

    for event in controller.step() + controller.step():
        assert event.validate()



MISSING_ABSTRACT_METHODS = "missing BaseManager abstract methods, see #34"


@pytest.mark.parametrize("manager_class", [
    ProcessManager,
    pytest.param(MemoryManager, marks=pytest.mark.xfail(reason=MISSING_ABSTRACT_METHODS, raises=TypeError, strict=True)),
    pytest.param(FileManager, marks=pytest.mark.xfail(reason=MISSING_ABSTRACT_METHODS, raises=TypeError, strict=True)),
])
def test_manager_registers_with_schema_name(manager_class):
    with open(SCHEMA_PATH) as f:
        schema_names = json.load(f)["properties"]["manager"]["enum"]
    controller = SimulationController()
    manager = manager_class()

    controller.register_manager(manager)

    assert manager.name in schema_names
    assert controller.get_manager(manager.name) is manager
