import time

import pandas as pd
import streamlit as st
from src.core.controller_api import RunStatus, Snapshot
from src.dashboard.manager_view import ManagerView
from src.dashboard.config_sidebar import render_network_sidebar, describe_network_config

from src.dashboard.network_topology import link_usage, topology_dot, usage_chart
from src.dashboard.run_controls import render_run_controls


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
        render_run_controls(controller, snapshot, prefix="network")

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

    if nodes and links and net_mgr:
        render_topology(net_mgr, nodes, links)

    st.markdown("---")
    q_col1, q_col2 = st.columns(2)
    with q_col1:
        st.markdown("**Queued Packets**")
        st.dataframe(pd.DataFrame(net_state.get("queued_packets", [])), hide_index=True, width="stretch")
    with q_col2:
        st.markdown("**Delivered & Dropped Packets**")
        combined = net_state.get("delivered_packets", []) + net_state.get("dropped_packets", [])
        st.dataframe(pd.DataFrame(combined), hide_index=True, width="stretch")


def render_topology(net_mgr, nodes: list, links: list) -> None:
    with st.container(border=True):
        st.markdown("**Network topology and selected route**")
        source_col, dest_col = st.columns(2)
        source = source_col.selectbox("Route from", nodes, key="network-route-source")
        dest = dest_col.selectbox("Route to", nodes, index=len(nodes) - 1, key="network-route-dest")
        route, cost = net_mgr.find_route(source, dest)
        st.graphviz_chart(topology_dot(nodes, links, route))
        if route:
            st.caption(f"Selected route: {' → '.join(route)} (total latency {cost:g} ms). "
                       "Thick blue links are the route; dashed links labeled DOWN have failed.")
        else:
            st.error(f"{dest} is unreachable from {source}: no route over links that are UP.")

    with st.container(border=True):
        st.markdown("**Link utilization**")
        usage = link_usage(st.session_state.get("events", []), links)
        if any(row["packets"] for row in usage):
            st.altair_chart(usage_chart(usage), width="stretch")
            with st.expander("Data table: link utilization"):
                st.dataframe(usage, hide_index=True)
        else:
            st.caption("No packets delivered yet. Press Step or Run.")


VIEW = ManagerView(
    name="Network",
    manager="Network",
    render_sidebar=render_network_sidebar,
    describe_config=describe_network_config,
    render_content=render_network_content,
)