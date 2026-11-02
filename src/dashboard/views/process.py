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
import time

import altair as alt
import pandas as pd
import streamlit as st
from src.core.controller_api import RunConfig, RunStatus, Snapshot
from src.dashboard.config_sidebar import render_process_settings
from src.dashboard.manager_view import ManagerView

AUTOPLAY = "process-autoplay"
LAST_STEP = "process-last-step"


def describe_config(config: RunConfig) -> str:
    process = config.process
    quantum = f"{process.quantum_ms} ms" if process.quantum_ms is not None else "–"
    return f"Policy: {process.policy.value} · Quantum: {quantum} · Context switch: {process.context_switch_ms} ms"


def _record(events: list) -> None:
    st.session_state.events = [*st.session_state.get("events", []), *events]
    st.rerun()


@st.fragment(run_every=1)
def _autoplay(controller) -> None:
    # The full rerun that each step triggers also calls this; skip it so steps stay a second apart.
    if time.monotonic() - st.session_state.get(LAST_STEP, 0.0) < 0.9:
        return
    st.session_state[LAST_STEP] = time.monotonic()
    _record(controller.step().events)


def render_process_content(snapshot: Snapshot) -> str:
    controller = st.session_state.get("controller")
    proc_mgr = None
    if controller and hasattr(controller, "engine"):
        proc_mgr = controller.engine.get_manager("Process")
    else:
        st.warning("Controller not initialized.")
    
    # Simulation Execution Controls
    if controller and hasattr(controller, "engine"):
        can_advance = snapshot.status in (RunStatus.READY, RunStatus.PAUSED)
        if not can_advance:
            st.session_state[AUTOPLAY] = False
        playing = st.session_state.get(AUTOPLAY, False)

        with st.container(horizontal=True):
            if st.button("", icon=":material/play_arrow:", key="process-run", disabled=not can_advance or playing,
                         help="Run (one tick per second)"):
                st.session_state[AUTOPLAY] = True
                st.rerun()
            if st.button("", icon=":material/pause:", key="process-pause", disabled=not playing, help="Pause"):
                st.session_state[AUTOPLAY] = False
                controller.pause()
                st.rerun()
            if st.button("", icon=":material/skip_next:", key="process-step", disabled=not can_advance or playing,
                         help="Step (1 tick)"):
                _record(controller.step().events)
            if st.button("", icon=":material/fast_forward:", key="process-run-to-end", disabled=not can_advance,
                         help="Run to completion"):
                st.session_state[AUTOPLAY] = False
                _record(controller.run().events)
            if st.button("", icon=":material/replay:", key="process-reset",
                         disabled=snapshot.status == RunStatus.NOT_LOADED, help="Reset"):
                st.session_state[AUTOPLAY] = False
                controller.reset()
                st.session_state.events = []
                st.rerun()

        status = "running" if playing else snapshot.status.value
        st.markdown(f"**Current Simulation Tick:** `{snapshot.tick} ms` · **Status:** `{status}`")
        if playing:
            _autoplay(controller)

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