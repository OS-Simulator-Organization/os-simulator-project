import heapq
import pytest
from src.core.events import EventRecord


def make_event(timestamp: float, event_type: str = "TEST_EVENT", entity_id: str = "E1") -> EventRecord:
    return EventRecord(
        timestamp=timestamp,
        manager="Process",
        event_type=event_type,
        entity_id=entity_id,
        action="TEST_ACTION",
        previous_state="NEW",
        new_state="READY",
        outcome="SUCCESS",
        duration_or_cost=1.0,
        explanatory_message="Test event record",
    )


def test_events_heapq_ordering_by_timestamp():
    """Verifies that events pop in strict ascending timestamp order regardless of insertion order."""
    evt1 = make_event(timestamp=10.0, entity_id="E10")
    evt2 = make_event(timestamp=2.0, entity_id="E2")
    evt3 = make_event(timestamp=5.5, entity_id="E5")

    heap = []
    heapq.heappush(heap, evt1)
    heapq.heappush(heap, evt2)
    heapq.heappush(heap, evt3)

    popped = [heapq.heappop(heap) for _ in range(3)]
    assert [e.timestamp for e in popped] == [2.0, 5.5, 10.0]
    assert [e.entity_id for e in popped] == ["E2", "E5", "E10"]


def test_events_deterministic_tie_breaking():
    """Verifies that events with identical timestamps do not raise comparison errors and preserve FIFO order."""
    evt_a = make_event(timestamp=5.0, entity_id="FIRST")
    evt_b = make_event(timestamp=5.0, entity_id="SECOND")

    heap = []
    heapq.heappush(heap, evt_a)
    heapq.heappush(heap, evt_b)

    first = heapq.heappop(heap)
    second = heapq.heappop(heap)

    assert first.timestamp == second.timestamp == 5.0
    assert first.entity_id == "FIRST"
    assert second.entity_id == "SECOND"


def test_event_schema_validation():
    """Verifies that EventRecord converts to dict and validates against event_schema.json."""
    evt = make_event(timestamp=0.0)
    assert evt.validate() is True