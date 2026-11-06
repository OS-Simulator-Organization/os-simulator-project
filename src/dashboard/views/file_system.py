import streamlit as st
from src.core.controller_api import Snapshot
from src.dashboard.manager_view import ManagerView

def _get_val(metrics_dict: dict, key: str) -> int:
    """Helper to safely extract metric values whether they are ints or Metric objects."""
    val = metrics_dict.get(key, 0)
    if hasattr(val, "value"):
        return int(val.value)
    return int(val) if val is not None else 0

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
    reads = _get_val(file_metrics, "reads_count")
    writes = _get_val(file_metrics, "writes_count")
    bytes_r = _get_val(file_metrics, "bytes_read")
    bytes_w = _get_val(file_metrics, "bytes_written")

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
    render_content=render_file_content,
)