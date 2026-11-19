import time

import pandas as pd
import streamlit as st
from src.core.controller_api import RunStatus, Snapshot
from src.dashboard.manager_view import ManagerView
from src.dashboard.config_sidebar import render_network_sidebar, describe_network_config

AUTOPLAY = "network-autoplay"
LAST_STEP = "network-last-step"


def _record(events: list) -> None:
    st.session_state.events = [*st.session_state.get("events", []), *events]
    st.rerun()


@st.fragment(run_every=1)
def _autoplay(controller) -> None:
    if time.monotonic() - st.session_state.get(LAST_STEP, 0.0) < 0.9:
        return
    st.session_state[LAST_STEP] = time.monotonic()
    _record(controller.step().events)


def render_network_content(snapshot: Snapshot) -> None:
    st.subheader("Network Manager Workspace")

    controller = st.session_state.get("controller")
    net_mgr = None
    if controller and hasattr(controller, "engine"):
        net_mgr = controller.engine.get_manager("Network")
    else:
        st.warning("Controller not initialized.")

    # Playback controls matching Process & Device views
    if controller and hasattr(controller, "engine"):
        can_advance = snapshot.status in (RunStatus.READY, RunStatus.PAUSED)
        if not can_advance:
            st.session_state[AUTOPLAY] = False
        playing = st.session_state.get(AUTOPLAY, False)

        with st.container(horizontal=True):
            if st.button("", icon=":material/play_arrow:", key="network-run", disabled=not can_advance or playing,
                         help="Run (one tick per second)"):
                st.session_state[AUTOPLAY] = True
                st.rerun()
            if st.button("", icon=":material/pause:", key="network-pause", disabled=not playing, help="Pause"):
                st.session_state[AUTOPLAY] = False
                controller.pause()
                st.rerun()
            if st.button("", icon=":material/skip_next:", key="network-step", disabled=not can_advance or playing,
                         help="Step (1 tick)"):
                _record(controller.step().events)
            if st.button("", icon=":material/fast_forward:", key="network-run-to-end", disabled=not can_advance,
                         help="Run to completion"):
                st.session_state[AUTOPLAY] = False
                _record(controller.run().events)
            if st.button("", icon=":material/replay:", key="network-reset",
                         disabled=snapshot.status == RunStatus.NOT_LOADED, help="Reset"):
                st.session_state[AUTOPLAY] = False
                controller.reset()
                st.session_state.events = []
                st.rerun()

        status = "running" if playing else snapshot.status.value
        st.markdown(f"**Current Simulation Tick:** `{snapshot.tick} ms` · **Status:** `{status}`")
        if playing:
            _autoplay(controller)

    raw_metrics = snapshot.metrics.get("Network", {}) if snapshot and snapshot.metrics else {}

    def get_metric_val(key: str, default: float = 0.0) -> float:
        metric = raw_metrics.get(key)
        if metric is not None and hasattr(metric, "value"):
            return metric.value
        return default

    m_cols = st.columns(4)
    m_cols[0].metric("Delivered Packets", int(get_metric_val("delivered_packets", 0)))
    m_cols[1].metric("Dropped Packets", int(get_metric_val("dropped_packets", 0)))
    m_cols[2].metric("Queued Packets", int(get_metric_val("queued_packets", 0)))
    m_cols[3].metric("Avg Latency", f"{get_metric_val('avg_network_latency', 0.0):.2f} ms")

    net_state = net_mgr.snapshot() if net_mgr and hasattr(net_mgr, "snapshot") else {}
    topology = net_state.get("topology", {})
    nodes = topology.get("nodes", [])
    links = topology.get("links", [])

    st.markdown("---")
    st.markdown("### Topology & Link Controls")
    if nodes:
        st.write(f"**Nodes:** {', '.join(nodes)} · **Policy:** `{net_state.get('queue_policy', 'FIFO')}`")

    if links:
        st.dataframe(pd.DataFrame(links), hide_index=True, width="stretch")
        if net_mgr:
            link_cols = st.columns(len(links))
            for idx, lk in enumerate(links):
                edge = lk["edge"]
                is_up = lk["status"] == "UP"
                with link_cols[idx]:
                    if is_up:
                        if st.button(f"Fail {edge}", key=f"fail-{edge}"):
                            net_mgr.fail_link(edge)
                            st.rerun()
                    else:
                        if st.button(f"Recover {edge}", key=f"recover-{edge}"):
                            net_mgr.recover_link(edge)
                            st.rerun()

    st.markdown("---")
    q_col1, q_col2 = st.columns(2)
    with q_col1:
        st.markdown("**Queued Packets**")
        st.dataframe(pd.DataFrame(net_state.get("queued_packets", [])), hide_index=True, width="stretch")
    with q_col2:
        st.markdown("**Delivered & Dropped Packets**")
        combined = net_state.get("delivered_packets", []) + net_state.get("dropped_packets", [])
        st.dataframe(pd.DataFrame(combined), hide_index=True, width="stretch")


VIEW = ManagerView(
    name="Network",
    manager="Network",
    render_sidebar=render_network_sidebar,
    describe_config=describe_network_config,
    render_content=render_network_content,
)