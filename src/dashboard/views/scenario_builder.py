import json
import re
import pandas as pd
import streamlit as st
from typing import Any, Dict, List, Tuple
from src.dashboard.manager_view import ManagerView
from src.core.controller_api import RunConfig, Snapshot
from src.dashboard.config_sidebar import SCENARIO

DEFAULT_WORKLOAD = [
    {"pid": "P1", "arrival_time": 0, "burst_time": 8, "priority": 3, "owner_id": "user1"},
    {"pid": "P2", "arrival_time": 1, "burst_time": 4, "priority": 1, "owner_id": "user1"},
    {"pid": "P3", "arrival_time": 2, "burst_time": 9, "priority": 4, "owner_id": "user1"},
    {"pid": "P4", "arrival_time": 3, "burst_time": 5, "priority": 2, "owner_id": "user1"},
]
REQUIRED_COLUMNS = ["pid", "arrival_time", "burst_time"]

# Single shared default memory trace matching the baseline requirements
DEFAULT_TRACE = ["0x0040", "0x10A0", "0x0044", "0x20B0"]
MAX_TRACE_ROWS = 200



def validate_workload(df: pd.DataFrame) -> List[str]:
    """Validates custom process workload"""
    if df.empty:
        return ["Workload cannot be empty."]
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        return [f"Missing required column(s): {', '.join(missing)}."]

    errors = []
    if not df["pid"].is_unique:
        errors.append("Process IDs must be unique.")

    pid_format = re.compile(r"^P\d+$")

    arrival = pd.to_numeric(df["arrival_time"], errors="coerce")
    burst = pd.to_numeric(df["burst_time"], errors="coerce")
    for i, pid in enumerate(df["pid"]):
        if pd.isna(pid) or not str(pid).strip():
            errors.append(f"Row {i + 1}: Process ID cannot be empty.")
        else:
            pid_str = str(pid).strip()
            if not pid_format.match(pid_str):
                errors.append(f"Row {i + 1} ('{pid_str}'): Process ID must follow the 'P#' format (e.g., P1, P2).")
                
        if pd.isna(arrival.iloc[i]) or arrival.iloc[i] < 0:
            errors.append(f"P{i + 1}: Arrival time must be >= 0.")
        if pd.isna(burst.iloc[i]) or burst.iloc[i] <= 0:
            errors.append(f"P{i + 1}: Burst time must be > 0.")
    return errors

def validate_trace(df: pd.DataFrame) -> Tuple[List[str], List[Any]]:
    """Validates the memory trace table."""
    errors = []
    parsed_trace = []
    
    if df.empty:
        return ["Memory trace cannot be empty."], []
    
    if len(df) > MAX_TRACE_ROWS:
        errors.append(f"Trace table cannot exceed {MAX_TRACE_ROWS} rows.")

    # Identify the target address column (defaults to 'address' or the first column)
    col_name = "address" if "address" in df.columns else df.columns[0]

    for index, value in enumerate(df[col_name]):
        if pd.isna(value) or str(value).strip() == "":
            continue

        val_str = str(value).strip()
        try:
            if val_str.startswith("0x") or val_str.startswith("0X"):
                addr = int(val_str, 16)
            else:
                addr = int(val_str)
                
            if addr < 0:
                errors.append(f"Trace Row {index + 1}: Address must be non-negative.")
            parsed_trace.append(val_str)
        except ValueError:
            errors.append(f"Trace Row {index + 1} ('{val_str}'): Must be valid hex (e.g. 0x00A) or decimal.")
        
    return errors, parsed_trace

def to_workload(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Turns a validated table into the records expected by the controller."""
    workload = df.reindex(columns=[*REQUIRED_COLUMNS, "priority", "owner_id"])
    workload["priority"] = pd.to_numeric(workload["priority"], errors="coerce").fillna(1)
    workload["owner_id"] = workload["owner_id"].astype(object).fillna("default_user")
    return workload.to_dict(orient="records")

def read_workload_file(uploaded_file) -> pd.DataFrame:
    if uploaded_file.name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    return pd.DataFrame(json.load(uploaded_file))

def render_scenario_builder(snapshot: Snapshot) -> None:
    state = st.session_state
    st.write("Double-click cells to edit. Use the bottom empty row to add. Select rows to delete.")
    
    if "current_workload" not in state:
        state.current_workload = pd.DataFrame(DEFAULT_WORKLOAD)
        state.editor_version = 0

    # Initialize single shared trace state
    if "current_trace" not in state:
        init_rows = max(5, len(DEFAULT_TRACE))
        trace_list = list(DEFAULT_TRACE) + [None] * (init_rows - len(DEFAULT_TRACE))
        state.current_trace = pd.DataFrame({"address": trace_list})

    col1, col2 = st.columns([2, 1], gap="medium")
    # Process table builder
    with col1:
        st.markdown("### 1. Process Workload")
        st.write("(Hex or Decimal, Empty cells permitted)")
        edited_workload_df = st.data_editor(
            state.current_workload,
            num_rows="dynamic",
            width="stretch",
            key=f"process_editor_{state.editor_version}",
        )
    with col2:
        st.markdown("### 2. Memory Trace")
        st.write("(Hex or Decimal, Empty cells permitted)")
        edited_trace_df = st.data_editor(
            state.current_trace,
            num_rows="dynamic",
            width="stretch",
            key=f"trace_editor_{state.editor_version}",
        )
        state.current_trace = edited_trace_df

    # Process import file region
    uploaded_file = st.file_uploader("Import Process Workload (JSON/CSV)", type=["json", "csv"])
    if uploaded_file is not None and uploaded_file.file_id != state.get("imported_file_id"):
        state.imported_file_id = uploaded_file.file_id
        try:
            state.current_workload = read_workload_file(uploaded_file)
            state.editor_version += 1  
            st.success("File imported successfully!")
        except Exception as e:
            st.error(f"Import failed: {e}")

    # Button that validates and loads scenario
    if st.button("Validate & Apply Scenario", type="primary"):
        workload_errors = validate_workload(edited_workload_df)
        trace_errors, parsed_trace = validate_trace(edited_trace_df)
        
        all_errors = workload_errors + trace_errors
        if all_errors:
            for err in all_errors:
                st.error(err)
        else:
            state["custom_workload"] = to_workload(edited_workload_df)
            state["custom_trace"] = parsed_trace  # Stored as a list
            state["pending_scenario"] = "custom"
            st.success("Scenario validated! Press Load and reset in the sidebar to run it.")

def describe_config(config: RunConfig) -> str:
    return "Add, edit, remove, import, and validate custom workloads and shared memory traces."

VIEW = ManagerView(
    name="Scenario Builder",
    manager="None",
    describe_config=describe_config,
    render_content=render_scenario_builder,
)