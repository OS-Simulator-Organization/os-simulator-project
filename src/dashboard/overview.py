"""Overview tab: manager status cards, current time, active scenario, run state,
warnings and a system summary (spec section 5)."""

from collections import Counter
from typing import Any, Dict, List

import streamlit as st

from src.core.controller_api import RunStatus, Snapshot
from src.dashboard.config_sidebar import config_errors, read_config

# (manager name used in events and metrics, label shown on the card)
MANAGERS = [
    ("Process", "Process"),
    ("Memory", "Memory"),
    ("File", "File System"),
    ("Device", "Device"),
    ("Network", "Network"),
    ("Security", "Security"),
    ("Parallel", "Parallel"),
]
PROBLEM_OUTCOMES = ("FAILURE", "ERROR", "DENIED")

ACTIVE = ":material/check_circle: Active"
WAITING = ":material/hourglass_empty: Waiting for a run"
NOT_CONNECTED = ":material/link_off: Not connected yet"


def manager_cards(snapshot: Snapshot, events: list, registered: List[str]) -> List[Dict[str, Any]]:
    """One row per manager. A manager is only active once it's registered with the controller and a run is loaded."""
    cards = []
    for name, label in MANAGERS:
        own = [e for e in events if e.manager == name]
        if name not in registered:
            status = NOT_CONNECTED
        elif snapshot.status is RunStatus.NOT_LOADED:
            status = WAITING
        else:
            status = ACTIVE
        cards.append({
            "manager": label,
            "status": status,
            "events": len(own),
            "problems": sum(e.outcome in PROBLEM_OUTCOMES for e in own),
        })
    return cards


def event_summary(events: list) -> List[Dict[str, Any]]:
    """Events per manager, split by outcome."""
    counts = Counter((e.manager, e.outcome) for e in events)
    outcomes = sorted({outcome for _, outcome in counts})
    return [
        {"manager": manager, **{o: counts[(manager, o)] for o in outcomes},
         "total": sum(counts[(manager, o)] for o in outcomes)}
        for manager in sorted({manager for manager, _ in counts})
    ]


def warnings(snapshot: Snapshot, events: list, cards: List[Dict[str, Any]]) -> List[str]:
    config = read_config()
    messages = list(config_errors(config))
    if snapshot.status is not RunStatus.NOT_LOADED and config != snapshot.config:
        messages.append("Sidebar settings differ from the loaded run. Press Load and reset to apply them.")
    missing = [c["manager"] for c in cards if c["status"] == NOT_CONNECTED]
    if missing:
        messages.append(f"Not connected to the controller yet: {', '.join(missing)}.")
    problems = sum(c["problems"] for c in cards)
    if problems:
        messages.append(f"{problems} failed or denied operation(s) so far. Filter by outcome in the Event Explorer.")
    return messages


def render_overview(controller, snapshot: Snapshot, events: list) -> None:
    st.subheader("OS Simulator Overview")
    registered = list(controller.engine.managers) if hasattr(controller, "engine") else []

    time_col, scenario_col, status_col, seed_col = st.columns(4)
    time_col.metric("Current time", f"{snapshot.tick} ms")
    scenario_col.metric("Active scenario", snapshot.config.scenario_id if snapshot.run_id else "–")
    status_col.metric("Run state", snapshot.status.value)
    seed_col.metric("Seed", snapshot.config.seed if snapshot.run_id else "–")

    cards = manager_cards(snapshot, events, registered)
    for message in warnings(snapshot, events, cards):
        st.warning(message, icon=":material/warning:")

    st.markdown("**Manager status**")
    columns = st.columns(4)
    for index, card in enumerate(cards):
        with columns[index % 4].container(border=True):
            st.markdown(f"**{card['manager']}**  \n{card['status']}")
            st.caption(f"{card['events']} events · {card['problems']} failed or denied")

    st.markdown("**System summary: events by manager and outcome**")
    summary = event_summary(events)
    if summary:
        st.dataframe(summary, hide_index=True)
    else:
        st.caption("No events yet. Load a run and press Step or Run on any manager tab.")

    st.divider()
    st.markdown("""
    Welcome to the **OS Simulator**. This platform models operating system subsystems in real time and demonstrates cross-manager execution dynamics.

    ### Subsystems Supported
    * **Process Subsystem:** Models CPU scheduling algorithms (Round Robin, FCFS, Priority, SJF), context switching, and Gantt charts.
    * **Memory Subsystem:** Simulates virtual memory paging, page fault handling, frame allocations, and replacement policies (FIFO, LRU).
    * **File Subsystem:** Manages hierarchical file trees, permissions, file creation/deletion, and dynamic I/O request queues.
    * **Event Engine:** Dispatches synchronized simulation ticks across all managers and streams real-time `EventRecord` logs.

    ---
    ### Quick Start
    1. Select a **Scenario** (e.g., `baseline`) in the **Global** sidebar panel.
    2. Click **Load and reset** to initialize the simulation engine.
    3. Step or run the engine using the playback controls on any manager view.
    """)
