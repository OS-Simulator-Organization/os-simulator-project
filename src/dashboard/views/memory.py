import time

import pandas as pd
import streamlit as st
from src.core.controller_api import RunConfig, RunStatus, Snapshot
from src.dashboard.config_sidebar import render_memory_settings
from src.dashboard.manager_view import ManagerView

AUTOPLAY = "memory-autoplay"
LAST_STEP = "memory-last-step"


def describe_config(config: RunConfig) -> str:
    mem = config.memory
    return f"Algorithm: {mem.algorithm.value} · Page size: {mem.page_size} bytes · Frames: {mem.total_frames} · Fault latency: {mem.fault_latency} ticks"


def _record(events: list) -> None:
    st.session_state.events = [*st.session_state.get("events", []), *events]
    st.rerun()


@st.fragment(run_every=1)
def _autoplay(controller) -> None:
    # Skip if step was triggered recently to keep ticks spaced apart
    if time.monotonic() - st.session_state.get(LAST_STEP, 0.0) < 0.9:
        return
    st.session_state[LAST_STEP] = time.monotonic()
    _record(controller.step().events)


def render_memory_content(snapshot: Snapshot) -> None:
    controller = st.session_state.get("controller")
    mem_mgr = None
    if controller and hasattr(controller, "engine"):
        mem_mgr = controller.engine.get_manager("Memory")
    else:
        st.warning("Controller not initialized.")
    
    # Simulation Execution Controls (matching process view style)
    if controller and hasattr(controller, "engine"):
        can_advance = snapshot.status in (RunStatus.READY, RunStatus.PAUSED)
        if not can_advance:
            st.session_state[AUTOPLAY] = False
        playing = st.session_state.get(AUTOPLAY, False)

        with st.container(horizontal=True):
            if st.button("", icon=":material/play_arrow:", key="memory-run", disabled=not can_advance or playing,
                         help="Run (one tick per second)"):
                st.session_state[AUTOPLAY] = True
                st.rerun()
            if st.button("", icon=":material/pause:", key="memory-pause", disabled=not playing, help="Pause"):
                st.session_state[AUTOPLAY] = False
                controller.pause()
                st.rerun()
            if st.button("", icon=":material/skip_next:", key="memory-step", disabled=not can_advance or playing,
                         help="Step (1 tick)"):
                _record(controller.step().events)
            if st.button("", icon=":material/fast_forward:", key="memory-run-to-end", disabled=not can_advance,
                         help="Run to completion"):
                st.session_state[AUTOPLAY] = False
                _record(controller.run().events)
            if st.button("", icon=":material/replay:", key="memory-reset",
                         disabled=snapshot.status == RunStatus.NOT_LOADED, help="Reset"):
                st.session_state[AUTOPLAY] = False
                controller.reset()
                st.session_state.events = []
                st.rerun()

        status = "running" if playing else snapshot.status.value
        st.markdown(f"**Current Simulation Tick:** `{snapshot.tick} ms` · **Status:** `{status}`")
        if playing:
            _autoplay(controller)

    # Pull memory manager snapshot state
    mgr_state = mem_mgr.snapshot() if mem_mgr and hasattr(mem_mgr, "snapshot") else {}


    mem_metrics = snapshot.metrics.get("Memory", {})
    p_hits = int(mem_metrics.get("page_hits", type("M", (), {"value": 0})).value)
    p_faults = int(mem_metrics.get("page_faults", type("M", (), {"value": 0})).value)
    hit_rate = float(mem_metrics.get("page_hit_rate", type("M", (), {"value": 0.0})).value) * 100
    avg_access = float(mem_metrics.get("avg_access_time", type("M", (), {"value": 0.0})).value)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Page Hits", p_hits)
    c2.metric("Page Faults", p_faults)
    c3.metric("Hit Rate", f"{hit_rate:.1f}%")
    c4.metric("Avg Access Time", f"{avg_access} ms")

    st.divider()


    # Region 1: Physical Frames Table
    with st.container(border=True):
        st.markdown("**Physical Frames**")
        frames_data = mgr_state.get("frames", [])
        if frames_data:
            df_frames = pd.DataFrame(frames_data)
            st.dataframe(df_frames, hide_index=True)
        else:
            st.caption("No physical frames allocated yet.")

    # Region 2: Page Tables, Fault Latencies, and Trace Pointers
    col1, col2 = st.columns(2)
    
    with col1:
        with st.container(border=True):
            st.markdown("**Page Tables**")
            page_tables = mgr_state.get("page_tables", {})
            if page_tables:
                for pid, pt in page_tables.items():
                    st.markdown(f"##### Process `{pid}`")
                    if pt:
                        pt_df = pd.DataFrame(list(pt.items()), columns=["Virtual Page", "Physical Frame"])
                        st.dataframe(pt_df, hide_index=True)
                    else:
                        st.caption("No page mappings.")
            else:
                st.caption("No page tables initialized.")

    with col2:
        with st.container(border=True):
            st.markdown("**Fault Latencies & Trace Progress**")
            fault_latencies = mgr_state.get("fault_latencies", {})
            trace_pointers = mgr_state.get("trace_pointers", {})
            
            st.markdown("##### Active Fault Penalties")
            if fault_latencies:
                fl_df = pd.DataFrame(list(fault_latencies.items()), columns=["Process ID", "Remaining Ticks"])
                st.dataframe(fl_df, hide_index=True)
            else:
                st.caption("No active page fault latencies.")

            st.markdown("##### Trace Pointers")
            if trace_pointers:
                tp_df = pd.DataFrame(list(trace_pointers.items()), columns=["Process ID", "Current Index"])
                st.dataframe(tp_df, hide_index=True)
            else:
                st.caption("No trace pointers recorded.")


VIEW = ManagerView(
    name="Memory",
    manager="Memory",
    regions=("Physical Frames", "Page Tables"),
    actions=("Dump stats",),
    describe_config=describe_config,
    render_sidebar=render_memory_settings,  # Connected to config_sidebar.py
    render_content=render_memory_content,
)