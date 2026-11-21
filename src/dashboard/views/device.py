import io
import time

import altair as alt
import pandas as pd
import streamlit as st
from src.core.controller_api import RunStatus, Snapshot, RunConfig
from src.dashboard.manager_view import ManagerView
from src.dashboard.run_controls import render_run_controls

def render_device_sidebar():
    from src.dashboard.config_sidebar import render_device_settings
    render_device_settings()

def render(snapshot: Snapshot):
    st.subheader("Device Manager Workspace")
    
    controller = st.session_state.get("controller")
    
    # Simulation Execution Controls
    if controller and hasattr(controller, "engine"):
        render_run_controls(controller, snapshot, prefix="device")

    # Extract raw metrics safely
    raw_metrics = snapshot.metrics.get("Device", {}) if snapshot and snapshot.metrics else {}
    
    # Helper to safely extract numeric values from Controller Metric objects
    def get_metric_val(key, default=0.0):
        metric = raw_metrics.get(key)
        if metric is not None and hasattr(metric, "value"):
            return metric.value
        return default

    events = st.session_state.get("events", [])
    
    # Fallback default devices if controller or engine isn't initialized yet
    default_devices = {
        "DISK_1": {"status": "AVAILABLE", "head_pos": 0},
        "PRINTER_1": {"status": "AVAILABLE", "head_pos": 0},
        "KEYBOARD_1": {"status": "AVAILABLE", "head_pos": 0},
    }
    
    dev_state = {}
    if controller and hasattr(controller, "engine"):
        dev_mgr = controller.engine.get_manager("Device")
        if dev_mgr:
            dev_state = dev_mgr.snapshot()
            
    devices_dict = dev_state.get("devices", default_devices)

    # Top-level System Metric Cards using extracted .value numeric lookups
    cols = st.columns(4)
    cols[0].metric("Completed Requests", int(get_metric_val("completed_requests", 0)))
    cols[1].metric("Pending Queue", int(get_metric_val("pending_requests", 0)))
    cols[2].metric("Total Seek Distance", f"{int(get_metric_val('total_seek_distance', 0))} cyl")
    cols[3].metric("Device Failures", int(get_metric_val("device_failures", 0)))

    st.markdown("---")

    # 1. Detailed Representation of the Three Required Device Types
    st.markdown("### Simulated Hardware Devices (Disk, Printer, Keyboard)")
    
    if devices_dict:
        device_table_data = []
        d_cols = st.columns(len(devices_dict))
        
        for i, (dev_id, info) in enumerate(devices_dict.items()):
            status = info.get("status", "AVAILABLE")
            head_pos = info.get("head_pos", 0)
            
            # Map type label explicitly
            dev_type = "Storage Disk" if "DISK" in dev_id else ("Printer" if "PRINTER" in dev_id else "Keyboard")
            
            device_table_data.append({
                "Device ID": dev_id,
                "Type": dev_type,
                "Status": status,
                "Head / Position": f"{head_pos} cyl" if "DISK" in dev_id else "N/A"
            })

            with d_cols[i]:
                st.metric(
                    label=f"{dev_id} ({dev_type})", 
                    value=status, 
                    delta=f"Head: {head_pos}" if "DISK" in dev_id else "Ready"
                )

        st.markdown("**Device Registry Overview:**")
        st.dataframe(pd.DataFrame(device_table_data), hide_index=True, width="stretch")
    else:
        st.info("No devices registered.")

    st.markdown("---")

    # 2. Device Queue & Active Requests
    st.markdown("### Device Request Queues")
    q_col1, q_col2 = st.columns(2)
    with q_col1:
        st.markdown("**Pending / Queued Requests**")
        pending = dev_state.get("pending_requests", [])
        if pending:
            st.write(pending)
        else:
            st.caption("Queue is empty or run not loaded.")
    with q_col2:
        st.markdown("**Active Requests (In Progress)**")
        active = dev_state.get("active_requests", {})
        if active:
            st.json(active)
        else:
            st.caption("No active I/O requests.")

    st.markdown("---")

    # 3. Disk-Head Movement Plot
    st.markdown("### Disk-Head Movement Plot (`DISK_1` Trajectory)")
    head_history = dev_state.get("disk_head_movements", [])
    if head_history:
        df_head = pd.DataFrame(head_history)
        chart_head = alt.Chart(df_head).mark_line(point=True, color="#ff4b4b").encode(
            x=alt.X("timestamp:Q", title="Simulation Tick (ms)"),
            y=alt.Y("to:Q", title="Cylinder Position"),
            tooltip=["timestamp", "from", "to", "seek", "request_id"]
        ).properties(title="Disk Head Seek Trajectory over Time", height=220)
        st.altair_chart(chart_head, width="stretch")
    else:
        st.caption("No disk head movements recorded yet. Run simulation ticks to generate plot.")

    st.markdown("---")

    # 4. Request Timeline / Gantt Chart Across All Devices
    st.markdown("### Multi-Device Request Timeline")
    completed = dev_state.get("completed_requests", [])
    if completed:
        df_comp = pd.DataFrame(completed)
        if "arrival_time" in df_comp.columns and "completion_time" in df_comp.columns:
            chart_timeline = alt.Chart(df_comp).mark_bar().encode(
                x=alt.X("arrival_time:Q", title="Time (ms)"),
                x2="completion_time:Q",
                y=alt.Y("request_id:N", title="Request ID"),
                color=alt.Color("device_id:N", legend=alt.Legend(title="Device")),
                tooltip=["request_id", "device_id", "process_id", "arrival_time", "completion_time", "status"]
            ).properties(title="I/O Service Timeline by Device", height=200)
            st.altair_chart(chart_timeline, width="stretch")
    else:
        st.caption("No completed request timelines available yet.")

def describe_device_config(config: RunConfig) -> str:
    devices_cfg = getattr(config, "devices", None)
    policy = devices_cfg.disk_policy.value if devices_cfg and getattr(devices_cfg, "disk_policy", None) else "FCFS"
    return f"Disk policy: {policy}"

VIEW = ManagerView(
    name="Device",
    manager="Device",
    describe_config=describe_device_config,
    render_sidebar=render_device_sidebar,
    render_content=render,
    test_files=("tests/test_device_manager.py",),
)
