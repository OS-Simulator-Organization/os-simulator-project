from src.core.events import EventRecord
from src.dashboard.event_explorer import filter_events, severity


def event(time, manager="Process", entity="P1", event_type="PROCESS_DISPATCH", outcome="SUCCESS", correlation=None):
    return EventRecord(timestamp=time, manager=manager, event_type=event_type, entity_id=entity, action="A",
                       previous_state="", new_state="", outcome=outcome, correlation_id=correlation)


EVENTS = [
    event(0, correlation="scn-1"),
    event(3, manager="File", entity="P2", event_type="FILE_OP_ERROR", outcome="ERROR", correlation="scn-1"),
    event(5, manager="Security", entity="u_guest", event_type="SECURITY_ALERT", outcome="HIGH"),
    event(9, entity="P3", event_type="PROCESS_TERMINATE"),
]


def test_no_filters_match_everything():
    assert filter_events(EVENTS) == EVENTS


def test_time_range_is_inclusive():
    assert filter_events(EVENTS, time_range=(3, 5)) == EVENTS[1:3]


def test_manager_outcome_and_text_filters():
    assert filter_events(EVENTS, managers=["Process"]) == [EVENTS[0], EVENTS[3]]
    assert filter_events(EVENTS, outcomes=["ERROR"]) == [EVENTS[1]]
    assert filter_events(EVENTS, entity="u_GUEST") == [EVENTS[2]]
    assert filter_events(EVENTS, event_type="terminate") == [EVENTS[3]]


def test_correlation_id_traces_events_across_managers():
    assert filter_events(EVENTS, correlation_id="scn-1") == EVENTS[:2]


def test_severity_comes_from_security_alert_outcomes():
    assert [severity(e) for e in EVENTS] == ["", "", "HIGH", ""]
    assert filter_events(EVENTS, severities=["HIGH"]) == [EVENTS[2]]


def test_filters_combine():
    assert filter_events(EVENTS, time_range=(0, 9), managers=["Process"], entity="p3") == [EVENTS[3]]
