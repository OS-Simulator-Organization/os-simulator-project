"""Event Explorer tab: search and filter the shared event log by time, manager,
entity, event type, outcome, severity and correlation ID (spec section 5).

The event schema has no severity field yet. Security alerts store their
severity (LOW / MEDIUM / HIGH) in `outcome`, so severity is read from there;
every other event has no severity.
"""

from typing import Optional, Sequence, Tuple

import streamlit as st

SEVERITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")


def severity(event) -> str:
    return event.outcome if event.outcome in SEVERITIES else ""


def filter_events(
    events: Sequence,
    time_range: Optional[Tuple[float, float]] = None,
    managers: Sequence[str] = (),
    entity: str = "",
    event_type: str = "",
    outcomes: Sequence[str] = (),
    severities: Sequence[str] = (),
    correlation_id: str = "",
) -> list:
    """Empty filters match everything. Text filters match part of the value and ignore case."""

    def contains(value, text: str) -> bool:
        return not text or text.lower() in str(value or "").lower()

    return [
        e for e in events
        if (time_range is None or time_range[0] <= e.timestamp <= time_range[1])
        and (not managers or e.manager in managers)
        and contains(e.entity_id, entity)
        and contains(e.event_type, event_type)
        and (not outcomes or e.outcome in outcomes)
        and (not severities or severity(e) in severities)
        and contains(e.correlation_id, correlation_id)
    ]


def render_event_explorer(events: list) -> None:
    st.subheader("Event Explorer")
    if not events:
        st.caption("No events yet. Load a run and press Step or Run on any manager tab.")
        return

    first, last = min(e.timestamp for e in events), max(e.timestamp for e in events)
    time_range = None
    if last > first:
        time_range = st.slider("Time range (ms)", min_value=float(first), max_value=float(last),
                               value=(float(first), float(last)), step=1.0, key="explorer-time")

    manager_col, outcome_col, severity_col = st.columns(3)
    managers = manager_col.multiselect("Manager", sorted({e.manager for e in events}), key="explorer-manager")
    outcomes = outcome_col.multiselect("Outcome", sorted({e.outcome for e in events}), key="explorer-outcome")
    present = [s for s in SEVERITIES if any(severity(e) == s for e in events)]
    severities = severity_col.multiselect("Severity", present, key="explorer-severity",
                                          help="Only security alerts carry a severity.")

    entity_col, type_col, correlation_col = st.columns(3)
    entity = entity_col.text_input("Entity ID contains", key="explorer-entity")
    event_type = type_col.text_input("Event type contains", key="explorer-type")
    correlation_id = correlation_col.text_input("Correlation ID contains", key="explorer-correlation")

    matches = filter_events(events, time_range, managers, entity, event_type, outcomes, severities, correlation_id)
    st.caption(f"Showing {len(matches)} of {len(events)} events.")
    st.dataframe([e.to_dict() for e in matches], hide_index=True)
