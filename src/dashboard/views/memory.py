import time

import altair as alt
import pandas as pd
import streamlit as st
from src.core.controller_api import RunConfig, RunStatus, Snapshot
from src.dashboard.config_sidebar import render_memory_settings
from src.dashboard.manager_view import ManagerView
# from src.dashboard.memory_history import memory_history

AUTOPLAY = "memory-autoplay"
LAST_STEP = "memory-last-step"
HISTORY = "memory-history"

PROCESS_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
FREE_COLOR = "#d5d5d0"
HIT_COLOR = "#1baf7a"
FAULT_COLOR = "#e34948"


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
    hit_rate = float(mem_metrics.get("page_hit_rate", type("M", (), {"value": 0.0})).value)
    avg_access = float(mem_metrics.get("avg_access_time", type("M", (), {"value": 0.0})).value)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Page Hits", p_hits)
    c2.metric("Page Faults", p_faults)
    c3.metric("Hit Rate", f"{hit_rate:.2f}%")
    c4.metric("Avg Access Time", f"{avg_access} ms")

    st.divider()


    # Region 1: Physical Frames Table
    with st.container(border=True):
        st.markdown("**Physical Frames**")
        frames_data = mgr_state.get("frames", [])
        if frames_data:
            df_frames = pd.DataFrame(frames_data)
            st.dataframe(df_frames, hide_index=True)
            st.download_button("Download frames (CSV)", mem_mgr.export("csv"), "memory_frames.csv", "text/csv",
                               key="memory-frames-csv")
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

    
#     history = _history(snapshot)

#     # Region 3: Frame occupancy over time
#     with st.container(border=True):
#         st.markdown("**Frame occupancy over time**")
#         if history["frames"]:
#             frames = pd.DataFrame(history["frames"])
#             st.altair_chart(occupancy_chart(frames), width="stretch")
#             st.caption("Each cell is one frame at one tick, labeled with its page number. Grey cells are free.")
#             with st.expander("Data table: frame occupancy"):
#                 st.dataframe(frames, hide_index=True)
#             st.markdown("##### Evictions")
#             if history["evictions"]:
#                 st.dataframe(history["evictions"], hide_index=True)
#             else:
#                 st.caption("No pages evicted yet.")
#         else:
#             st.caption("No ticks run yet. Press Step or Run.")

#     # Region 4: Hit/fault timeline
#     with st.container(border=True):
#         st.markdown("**Page hits and faults over time**")
#         if history["accesses"]:
#             accesses = pd.DataFrame(history["accesses"])
#             st.altair_chart(access_chart(accesses), width="stretch")
#             with st.expander("Data table: hits and faults"):
#                 st.dataframe(accesses, hide_index=True)
#         else:
#             st.caption("No memory references yet.")


# def _history(snapshot: Snapshot) -> dict:
#     """Replays the loaded run up to the current tick, reusing the last replay while the tick hasn't changed."""
#     if snapshot.status is RunStatus.NOT_LOADED or snapshot.tick == 0:
#         return {"frames": [], "accesses": [], "evictions": []}
#     key = (snapshot.run_id, snapshot.tick)
#     cached = st.session_state.get(HISTORY)
#     if cached is None or cached[0] != key:
#         cached = (key, memory_history(snapshot.config, snapshot.tick))
#         st.session_state[HISTORY] = cached
#     return cached[1]


# def occupancy_chart(frames: pd.DataFrame) -> alt.LayerChart:
#     processes = sorted(p for p in frames["process"].unique() if p != "free")
#     colors = PROCESS_COLORS[:len(processes)] if len(processes) <= len(PROCESS_COLORS) else [PROCESS_COLORS[0]] * len(processes)
#     base = alt.Chart(frames).encode(
#         x=alt.X("tick:O", title="Simulation time (ms)"),
#         y=alt.Y("frame:O", title="Physical frame"),
#     )
#     cells = base.mark_rect(stroke="white", strokeWidth=1).encode(
#         color=alt.Color("process:N", title="Process",
#                         scale=alt.Scale(domain=[*processes, "free"], range=[*colors, FREE_COLOR])),
#         tooltip=[alt.Tooltip("tick:O", title="Tick (ms)"), alt.Tooltip("frame:O", title="Frame"),
#                  alt.Tooltip("contents:N", title="Contents")],
#     )
#     pages = base.transform_filter(alt.datum.process != "free").mark_text(fontSize=10, color="white").encode(
#         text=alt.Text("page:Q", format="d"))
#     return (cells + pages).properties(title="Frame occupancy over time (label = page number)")


# def access_chart(accesses: pd.DataFrame) -> alt.Chart:
#     return alt.Chart(accesses).mark_point(size=90, filled=True).encode(
#         x=alt.X("tick:Q", title="Simulation time (ms)", axis=alt.Axis(tickMinStep=1)),
#         y=alt.Y("result:N", title="Reference result", sort=["Hit", "Fault"]),
#         color=alt.Color("result:N", title="Result", scale=alt.Scale(domain=["Hit", "Fault"], range=[HIT_COLOR, FAULT_COLOR])),
#         shape=alt.Shape("result:N", scale=alt.Scale(domain=["Hit", "Fault"], range=["circle", "cross"])),
#         tooltip=[alt.Tooltip("tick:Q", title="Tick (ms)"), alt.Tooltip("result:N", title="Result")],
#     ).properties(title="Page hits and faults over time", height=140)


VIEW = ManagerView(
    name="Memory",
    manager="Memory",
    regions=("Physical Frames", "Page Tables"),
    actions=("Dump stats",),
    describe_config=describe_config,
    render_sidebar=render_memory_settings,
    render_content=render_memory_content,
    test_files=("tests/test_file_memory_integration.py",),
)