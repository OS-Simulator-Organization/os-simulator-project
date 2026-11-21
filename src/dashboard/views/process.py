# from src.core.controller_api import RunConfig
# from src.dashboard.config_sidebar import render_process_settings
# from src.dashboard.manager_view import ManagerView


# def describe_config(config: RunConfig) -> str:
#     process = config.process
#     quantum = f"{process.quantum_ms} ms" if process.quantum_ms is not None else "-"
#     return f"Policy: {process.policy.value} · Quantum: {quantum} · Context switch: {process.context_switch_ms} ms"


# VIEW = ManagerView(
#     name="Process",
#     manager="Process",
#     regions=("CPU Gantt chart", "Process table"),
#     actions=("Run process tests",),
#     describe_config=describe_config,
#     render_sidebar=render_process_settings,
# )

import io

import altair as alt
import pandas as pd
import streamlit as st
from src.core.controller_api import RunConfig, Snapshot
from src.dashboard.config_sidebar import render_process_settings
from src.dashboard.manager_view import ManagerView
from src.dashboard.process_timeline import state_intervals, timeline_chart, transitions
from src.dashboard.run_controls import render_run_controls

def describe_config(config: RunConfig) -> str:
    process = config.process
    quantum = f"{process.quantum_ms} ms" if process.quantum_ms is not None else "–"
    return f"Policy: {process.policy.value} · Quantum: {quantum} · Context switch: {process.context_switch_ms} ms"


def render_process_content(snapshot: Snapshot) -> str:
    controller = st.session_state.get("controller")
    proc_mgr = None
    if controller and hasattr(controller, "engine"):
        proc_mgr = controller.engine.get_manager("Process")
    else:
        st.warning("Controller not initialized.")
    
    # Simulation Execution Controls
    if controller and hasattr(controller, "engine"):
        render_run_controls(controller, snapshot, prefix="process")

    # Pull process manager state snapshot
    mgr_state = proc_mgr.snapshot() if proc_mgr and hasattr(proc_mgr, "snapshot") else {}

    # Region 1: CPU Gantt Chart
    with st.container(border=True):
        st.markdown("**CPU Gantt chart**")
        if proc_mgr and hasattr(proc_mgr, "gantt_ticks") and proc_mgr.gantt_ticks:
            # One row per [start, end) interval; "cs" and "idle" are scheduler overhead, not processes.
            intervals = pd.read_csv(io.StringIO(proc_mgr._gantt_chart()), dtype={"label": str})
            intervals["mid"] = (intervals.start + intervals.end) / 2
            intervals["lane"] = "CPU"
            overhead = intervals.label.isin(["idle", "cs"])
            pids = sorted(intervals.label[~overhead].unique())
            # Every interval shares the single "CPU" row.
            y = alt.Y("lane:N", title=None)
            # Processes get a color each; context switches are grey, and idle is faded grey.
            bars = alt.Chart(intervals).mark_bar(stroke="white", strokeWidth=1).encode(
                x=alt.X("start:Q", title="Time (ms)", scale=alt.Scale(domainMin=0)),
                x2="end:Q",
                y=y,
                color=alt.condition(alt.FieldOneOfPredicate("label", ["idle", "cs"]), alt.value("#A0A8B4"),
                                    alt.Color("label:N", scale=alt.Scale(domain=pids),
                                              legend=alt.Legend(title="Process", orient="bottom", direction="horizontal"))),
                opacity=alt.condition(alt.datum.label == "idle", alt.value(0.4), alt.value(1.0)),
                tooltip=["label", "start", "end"],
            )
            # PID labels centered on process bars, plus a dashed line at the current tick.
            labels = alt.Chart(intervals[~overhead]).mark_text(color="white", fontWeight="bold").encode(
                x="mid:Q", y=y, text="label:N")
            now = alt.Chart(pd.DataFrame({"t": [snapshot.tick]})).mark_rule(strokeDash=[4, 4], color="#D33").encode(x="t:Q")
            st.altair_chart((bars + labels + now).properties(
                title="CPU timeline (grey = context switch, faded = idle, red line = now)", height=60,
                # fit-x keeps the 60 px for the bar row; Streamlit's default "fit" would shrink it to nothing.
                autosize=alt.AutoSizeParams(type="fit-x", contains="padding")),
                width="stretch")
            with st.expander("Data table: CPU Gantt chart"):
                st.dataframe(intervals[["start", "end", "label"]], hide_index=True)
        else:
            st.caption("No CPU execution recorded yet. Press Step or Run.")

    # Region 2: Process state timeline (Running -> Blocked -> Ready, with the blocked reason)
    with st.container(border=True):
        st.markdown("**Process state timeline**")
        events = st.session_state.get("events", [])
        intervals = state_intervals(events, now=snapshot.tick)
        if intervals:
            st.altair_chart(timeline_chart(intervals), width="stretch")
            st.caption("Blocked stretches show which manager blocked the process in the tooltip and tables.")
            with st.expander("Data table: time in each state"):
                st.dataframe(intervals, hide_index=True)
            st.markdown("##### State transitions")
            st.dataframe(transitions(events), hide_index=True)
        else:
            st.caption("No state changes yet. Press Step or Run.")

    # Region 3: Process Table & Ready Queue
    with st.container(border=True):
        st.markdown("**Process table**")
        workload_data = mgr_state.get("workload", [])
        if workload_data:
            st.dataframe(workload_data, hide_index=True)
        else:
            st.caption("No processes loaded.")


VIEW = ManagerView(
    name="Process",
    manager="Process",
    regions=("CPU Gantt chart", "Process state timeline", "Process table"),
    actions=("Run process tests",),
    describe_config=describe_config,
    render_sidebar=render_process_settings,
    render_content=render_process_content,
)