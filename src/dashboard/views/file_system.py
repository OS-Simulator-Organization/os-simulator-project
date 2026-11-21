from typing import Any, Dict, List

import altair as alt
import pandas as pd
import streamlit as st
from src.core.controller_api import Snapshot
from src.dashboard.manager_view import ManagerView
from src.dashboard.run_controls import render_run_controls

BAR_COLOR = "#2a78d6"


def _get_val(metrics_dict: dict, key: str) -> int:
    """Helper to safely extract metric values whether they are ints or Metric objects."""
    val = metrics_dict.get(key, 0)
    if hasattr(val, "value"):
        return int(val.value)
    return int(val) if val is not None else 0


def flatten_tree(node: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Turns the nested tree from FileManager.snapshot() into one row per file or directory."""
    if not node:
        return []
    rows = [{
        "path": node["path"],
        "type": "directory" if node["is_dir"] else "file",
        "owner": node["owner_id"],
        "permissions": node["permissions"],
        "size (bytes)": node["size"],
    }]
    for child in node.get("children", {}).values():
        rows.extend(flatten_tree(child))
    return rows


def operation_log(events: list) -> List[Dict[str, Any]]:
    """File events in the order they happened."""
    return [
        {"time (ms)": e.timestamp, "process": e.entity_id, "command": e.action, "outcome": e.outcome,
         "details": e.explanatory_message}
        for e in events if e.manager == "File"
    ]


def operation_counts(log: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    counts: Dict[str, Dict[str, int]] = {}
    for row in log:
        command = counts.setdefault(row["command"], {"succeeded": 0, "failed": 0})
        command["succeeded" if row["outcome"] == "SUCCESS" else "failed"] += 1
    return [{"command": name, **values} for name, values in sorted(counts.items())]


def storage_chart(files: pd.DataFrame) -> alt.Chart:
    return alt.Chart(files).mark_bar(color=BAR_COLOR).encode(
        x=alt.X("size (bytes):Q", title="Size (bytes)"),
        y=alt.Y("path:N", title="File", sort="-x"),
        tooltip=["path", "size (bytes)", "owner"],
    ).properties(title="Storage used by each file")


def render_file_content(snapshot: Snapshot) -> None:
    controller = st.session_state.get("controller")
    file_mgr = controller.engine.get_manager("File") if controller and hasattr(controller, "engine") else None

    if not file_mgr:
        st.warning("File Manager not initialized in controller engine.")
        return

    render_run_controls(controller, snapshot, prefix="file")

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
    file_tree = file_state.get("file_tree", {})
    with st.container(border=True):
        st.markdown("**Live File Hierarchy Tree**")
        if file_tree:
            st.json(file_tree)
        else:
            st.caption("No files or directories currently created.")

    nodes = flatten_tree(file_tree)

    # Region 3: Metadata for the selected node
    with st.container(border=True):
        st.markdown("**Node metadata**")
        if nodes:
            path = st.selectbox("File or directory", [n["path"] for n in nodes], key="file-node")
            node = next(n for n in nodes if n["path"] == path)
            st.dataframe([{"field": key, "value": str(value)} for key, value in node.items()], hide_index=True)
        else:
            st.caption("No files or directories currently created.")

    # Region 4: Storage composition
    with st.container(border=True):
        st.markdown("**Storage composition**")
        files = pd.DataFrame([n for n in nodes if n["type"] == "file"])
        if not files.empty:
            st.caption(f"Storage used: {int(files['size (bytes)'].sum())} bytes in {len(files)} file(s).")
            st.altair_chart(storage_chart(files), width="stretch")
            with st.expander("Data table: storage by file"):
                st.dataframe(files, hide_index=True)
        else:
            st.caption("No files yet.")

    # Region 5: Chronological operation log and counts
    log = operation_log(st.session_state.get("events", []))
    with st.container(border=True):
        st.markdown("**Operation log**")
        if log:
            succeeded = sum(row["outcome"] == "SUCCESS" for row in log)
            ok_col, failed_col = st.columns(2)
            ok_col.metric("Successful operations", succeeded)
            failed_col.metric("Failed operations", len(log) - succeeded)
            st.dataframe(operation_counts(log), hide_index=True)
            st.dataframe(log, hide_index=True)
            st.caption("The File manager doesn't model per-command latency yet, so counts are shown instead.")
        else:
            st.caption("No file operations yet. Press Step or Run.")


VIEW = ManagerView(
    name="File System",
    manager="File",
    render_content=render_file_content,
    test_files=("tests/test_file_manager.py", "tests/test_file_memory_integration.py"),
)
