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
from src.core.controller_api import RunConfig, RunStatus, Snapshot
from src.dashboard.config_sidebar import render_process_settings
from src.dashboard.manager_view import ManagerView


def describe_config(config: RunConfig) -> str:
    process = config.process
    quantum = f"{process.quantum_ms} ms" if process.quantum_ms is not None else "–"
    return f"Policy: {process.policy.value} · Quantum: {quantum} · Context switch: {process.context_switch_ms} ms"


def _record(events: list) -> None:
    """Appends a step/run's events to the Event log, then redraws."""
    st.session_state.events = [*st.session_state.get("events", []), *events]
    st.rerun()


def render_process_content(snapshot: Snapshot) -> str:
    controller = st.session_state.get("controller")
    proc_mgr = None
    if controller and hasattr(controller, "engine"):
        proc_mgr = controller.engine.get_manager("Process")
    else:
        st.warning("Controller not initialized.")
    
    # Simulation Execution Controls (Step / Run / Pause / Reset)
    if controller and hasattr(controller, "engine"):
        can_advance = snapshot.status in (RunStatus.READY, RunStatus.PAUSED)
        step_col, run_col, pause_col, reset_col = st.columns(4)
        if step_col.button("Step (1 tick)", key="process-step", disabled=not can_advance, width="stretch"):
            _record(controller.step().events)
        if run_col.button("Run to completion", key="process-run", disabled=not can_advance, width="stretch"):
            _record(controller.run().events)
        # shortcut: run() is synchronous, so Pause only takes effect between reruns, not mid-run
        if pause_col.button("Pause", key="process-pause", disabled=not can_advance, width="stretch"):
            controller.pause()
            st.rerun()
        if reset_col.button("Reset", key="process-reset", disabled=snapshot.status == RunStatus.NOT_LOADED, width="stretch"):
            controller.reset()
            st.session_state.events = []
            st.rerun()

        until_col, until_btn_col, tick_col = st.columns([1, 1, 2], vertical_alignment="bottom")
        until_tick = until_col.number_input("Until tick", key="process-until-tick", min_value=1, value=10, step=1)
        if until_btn_col.button("Run until tick", key="process-run-until", disabled=not can_advance, width="stretch"):
            _record(controller.run(until_tick=int(until_tick)).events)
        tick_col.markdown(f"**Current Simulation Tick:** `{snapshot.tick} ms` · **Status:** `{snapshot.status.value}`")

    # Pull process manager state snapshot
    mgr_state = proc_mgr.snapshot() if proc_mgr and hasattr(proc_mgr, "snapshot") else {}

    # Region 1: CPU Gantt Chart
    with st.container(border=True):
        st.markdown("**CPU Gantt chart**")
        if proc_mgr and hasattr(proc_mgr, "gantt_ticks") and proc_mgr.gantt_ticks:
            intervals = pd.read_csv(io.StringIO(proc_mgr._gantt_chart()), dtype={"label": str})
            chart = alt.Chart(intervals).mark_bar().encode(
                x=alt.X("start:Q", title="Tick (ms)"),
                x2="end:Q",
                y=alt.Y("label:N", title=None),
                color=alt.Color("label:N", legend=None),
                tooltip=["label", "start", "end"],
            )
            st.altair_chart(chart, width="stretch")
        else:
            st.caption("No CPU execution recorded yet. Press Step or Run.")

    # Region 2: Process Table & Ready Queue
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
    regions=("CPU Gantt chart", "Process table"),
    actions=("Run process tests",),
    describe_config=describe_config,
    render_sidebar=render_process_settings,
    render_content=render_process_content,
)