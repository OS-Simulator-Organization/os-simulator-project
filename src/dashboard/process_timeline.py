"""Process state timeline (spec 5.1): process-state transitions and blocked reasons.

Every Process event records previous_state -> new_state, and block events say
which manager caused them ("Blocked by Memory manager"). Walking those events in
order gives how long each process spent in each state.
"""

from typing import Any, Dict, List

import altair as alt
import pandas as pd

STATE_LABELS = {"READY": "Ready", "RUNNING": "Running", "WAITING": "Blocked", "NEW": "New"}
STATE_COLORS = {"Running": "#2a78d6", "Ready": "#eda100", "Blocked": "#e34948", "New": "#c3c2b7"}


def transitions(events: list) -> List[Dict[str, Any]]:
    """Every Process state change, in order, with the reason when there is one."""
    return [
        {
            "time (ms)": e.timestamp,
            "process": e.entity_id,
            "from": STATE_LABELS.get(e.previous_state, e.previous_state.title()),
            "to": STATE_LABELS.get(e.new_state, e.new_state.title()),
            "reason": e.explanatory_message or e.action,
        }
        for e in events
        if e.manager == "Process" and e.previous_state != e.new_state
    ]


def state_intervals(events: list, now: int) -> List[Dict[str, Any]]:
    """One row per stretch of time a process spent in one state. Stretches still open end at `now`."""
    rows: List[Dict[str, Any]] = []
    current: Dict[str, Dict[str, Any]] = {}   # process -> the state it's in right now

    def close(open_row: Dict[str, Any], end: float) -> None:
        if end > open_row["start (ms)"]:
            rows.append({**open_row, "end (ms)": end, "duration (ms)": end - open_row["start (ms)"]})

    for change in transitions(events):
        process, time = change["process"], change["time (ms)"]
        if process in current:
            close(current.pop(process), time)
        if change["to"] != "Terminated":
            reason = change["reason"] if change["to"] == "Blocked" else ""
            current[process] = {"process": process, "state": change["to"], "start (ms)": time, "reason": reason}

    for open_row in current.values():
        close(open_row, now)
    return sorted(rows, key=lambda r: (r["process"], r["start (ms)"]))


def timeline_chart(intervals: List[Dict[str, Any]]) -> alt.Chart:
    states = [s for s in STATE_COLORS if any(r["state"] == s for r in intervals)]
    return alt.Chart(pd.DataFrame(intervals)).mark_bar(stroke="white", strokeWidth=1).encode(
        x=alt.X("start (ms):Q", title="Simulation time (ms)"),
        x2="end (ms):Q",
        y=alt.Y("process:N", title="Process"),
        color=alt.Color("state:N", title="State",
                        scale=alt.Scale(domain=states, range=[STATE_COLORS[s] for s in states])),
        tooltip=["process", "state", "start (ms)", "end (ms)", "reason"],
    ).properties(title="Process states over time (Running, Ready, Blocked)", height=40 + 30 * len({r["process"] for r in intervals}))
