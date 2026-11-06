import streamlit as st
from src.core.controller_api import Snapshot
from src.dashboard.manager_view import ManagerView

# #### ****MILESTONE 3: LIVE FILE SYSTEM VIEW RENDERING**** ####
def render_file_content(snapshot: Snapshot) -> None:
    controller = st.session_state.get("controller")
    file_mgr = controller.engine.get_manager("File") if controller and hasattr(controller, "engine") else None

    if not file_mgr:
        st.warning("File Manager not initialized in controller engine.")
        return

    # Extract dynamic metrics from live engine snapshot
    file_metrics = snapshot.metrics.get("File", {})
    file_state = file_mgr.snapshot()

    # Region 1: Live Operational Metrics
    m1, m2, m3, m4 = st.columns(4)
    reads = int(file_metrics.get("reads_count", type("M", (), {"value": 0})).value)
    writes = int(file_metrics.get("writes_count", type("M", (), {"value": 0})).value)
    bytes_r = int(file_metrics.get("bytes_read", type("M", (), {"value": 0})).value)
    bytes_w = int(file_metrics.get("bytes_written", type("M", (), {"value": 0})).value)

    m1.metric("Reads Executed", reads)
    m2.metric("Writes Executed", writes)
    m3.metric("Bytes Read", f"{bytes_r} B")
    m4.metric("Bytes Written", f"{bytes_w} B")

    st.divider()

    # Region 2: Interactive File System Hierarchy Tree
    with st.container(border=True):
        st.markdown("**Live File Hierarchy Tree**")
        file_tree = file_state.get("file_tree", {})
        if file_tree:
            st.json(file_tree)
        else:
            st.caption("No files or directories currently created.")


VIEW = ManagerView(
    name="File System",
    manager="File",
    render_content=render_file_content,  # #### ****MILESTONE 3: BIND LIVE CONTENT**** ####
)