import json
import re
import pandas as pd
import streamlit as st
from typing import Any, Dict, List, Tuple
from src.dashboard.manager_view import ManagerView
from src.core.controller_api import RunConfig, Snapshot

DEFAULT_WORKLOAD = [
    {"pid": "P1", "arrival_time": 0, "burst_time": 8, "priority": 3, "owner_id": "user1"},
    {"pid": "P2", "arrival_time": 1, "burst_time": 4, "priority": 1, "owner_id": "user1"},
]
REQUIRED_COLUMNS = ["pid", "arrival_time", "burst_time"]

DEFAULT_TRACES = {
    "P1": ["0x02E5F", "0x14B8", "10356", "0x3DDD"],
    "P2": ["0x267A", "0x5FC1"],
}
MAX_TRACE_ROWS = 200

def validate_workload(df: pd.DataFrame) -> List[str]:
    if df.empty:
        return ["Workload cannot be empty."]
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        return [f"Missing required column(s): {', '.join(missing)}."]

    errors = []
    if not df["pid"].is_unique:
        errors.append("Process IDs must be unique.")

    #This is the enforced format of all PIDs: must be P#
    pid_format = re.compile(r"^P\d+$")

    # Imported files can hold text in number columns; treat it as missing.
    arrival = pd.to_numeric(df["arrival_time"], errors="coerce")
    burst = pd.to_numeric(df["burst_time"], errors="coerce")
    for i, pid in enumerate(df["pid"]):
        if pd.isna(pid) or not str(pid).strip():
            errors.append(f"Row {i + 1}: Process ID cannot be empty.")
            pid = f"Row {i + 1}"
        else:
            pid_str = str(pid).strip()
            if not pid_format.match(pid_str):
                errors.append(f"Row {i + 1} ('{pid_str}'): Process ID must follow the 'P#' format (e.g., P1, P2).")
                
        if pd.isna(arrival.iloc[i]) or arrival.iloc[i] < 0:
            errors.append(f"{pid}: Arrival time must be >= 0.")
        if pd.isna(burst.iloc[i]) or burst.iloc[i] <= 0:
            errors.append(f"{pid}: Burst time must be > 0.")
    return errors

def validate_traces(df: pd.DataFrame, valid_pids: List[str]) -> Tuple[List[str], Dict[str, List[Any]]]:
    errors = []
    traces_dict = {}
    
    if len(df) > MAX_TRACE_ROWS:
        errors.append(f"Trace table cannot exceed {MAX_TRACE_ROWS} rows.")

    for pid in valid_pids:
        if pid not in df.columns:
            traces_dict[pid] = []
            continue
        
        pid_traces = []
        for index, value in enumerate(df[pid]):
            if pd.isna(value) or str(value).strip() == "":
                continue

            val_str = str(value).strip()
            try:
                if val_str.startswith("0x") or val_str.startswith("0X"):
                    addr = int(val_str, 16)
                else:
                    addr = int(val_str)
                if addr < 0:
                    errors.append(f"Trace [{pid}], Row {index + 1}: Address must be non-negative.")
                pid_traces.append(val_str)
            except ValueError:
                errors.append(f"Trace [{pid}], Row {index + 1} ('{val_str}'): Must be valid hex (e.g. 0x00A) or decimal.")
        
        traces_dict[pid] = pid_traces
    return errors, traces_dict

def to_workload(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Turns a validated table into the records RealController.load() expects, filling blank optional fields."""
    workload = df.reindex(columns=[*REQUIRED_COLUMNS, "priority", "owner_id"])
    workload["priority"] = pd.to_numeric(workload["priority"], errors="coerce").fillna(1)
    workload["owner_id"] = workload["owner_id"].astype(object).fillna("default_user")
    return workload.to_dict(orient="records")

def read_workload_file(uploaded_file) -> pd.DataFrame:
    if uploaded_file.name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    return pd.DataFrame(json.load(uploaded_file))

def render_scenario_builder(snapshot: Snapshot) -> None:
    st.caption("Add, edit, remove, import, and validate custom workloads.")
    state = st.session_state
    if "current_workload" not in state:
        state.current_workload = pd.DataFrame(DEFAULT_WORKLOAD)
        state.editor_version = 0

    if "current_traces" not in state:
        max_default_len = max((len(t) for t in DEFAULT_TRACES.values()), default=5)
        init_rows = max(5, max_default_len)
        
        default_trace_data = {}
        for pid, trace in DEFAULT_TRACES.items():
            default_trace_data[pid] = list(trace) + [None] * (init_rows - len(trace))
        state.current_traces = pd.DataFrame(default_trace_data, index=range(init_rows))

    uploaded_file = st.file_uploader("Import Workload (JSON/CSV)", type=["json", "csv"])
    # The uploader keeps its file across reruns, so import each file only once.
    if uploaded_file is not None and uploaded_file.file_id != state.get("imported_file_id"):
        state.imported_file_id = uploaded_file.file_id
        try:
            state.current_workload = read_workload_file(uploaded_file)
            state.editor_version += 1  # a new editor key drops edits made to the old table
            st.success("File imported successfully!")
        except Exception as e:
            st.error(f"Import failed: {e}")

    st.markdown("### 1. Process Workload")
    st.write("Double-click cells to edit. Use the bottom empty row to add. Select rows to delete.")
    edited_df = st.data_editor(
        state.current_workload,
        num_rows="dynamic",
        width="stretch",
        key=f"process_editor_{state.editor_version}",
    )

    # Extract current valid PIDs to dynamically update trace columns
    current_pids = [str(p).strip() for p in edited_df["pid"].dropna() if str(p).strip()]

    # Reconstruct or sync trace dataframe columns with current PIDs
    old_trace_df = state.get("current_traces", pd.DataFrame())
    current_row_count = len(old_trace_df) if not old_trace_df.empty else 5

    trace_data = {}
    for pid in current_pids:
        if pid in old_trace_df.columns:
            existing_col = old_trace_df[pid].tolist()
            if len(existing_col) < current_row_count:
                existing_col += [None] * (current_row_count - len(existing_col))
            else:
                existing_col = existing_col[:current_row_count]
            trace_data[pid] = existing_col
        else:
            trace_data[pid] = [None] * current_row_count
    
    if not trace_data:
        trace_data["P1"] = [None] * 5
        current_row_count = 5

    trace_df = pd.DataFrame(trace_data, index=range(current_row_count))
    state.current_traces = trace_df

    st.markdown("### 2. Process Memory Traces")
    st.write("(Hex or Decimal, Max 200 rows)")
    st.write("Columns automatically match list of PIDs above. Empty cells are allowed (no memory reference for that process tick)")
    
    edited_trace_df = st.data_editor(
        state.current_traces,
        num_rows="dynamic",
        width="stretch",
        key=f"trace_editor_{state.editor_version}",
    )

    if st.button("Validate & Apply Scenario", type="primary"):
        workload_errors = validate_workload(edited_df)
        trace_errors, parsed_traces = validate_traces(edited_trace_df, current_pids)
        
        all_errors = workload_errors + trace_errors
        if all_errors:
            for err in all_errors:
                st.error(err)
        else:
            state["custom_workload"] = to_workload(edited_df)
            state["custom_traces"] = parsed_traces
            state["current_traces"] = edited_trace_df
            st.success("Scenario validated! Press Load and reset in the sidebar to run it.")

def describe_config(config: RunConfig) -> str:
    workload = config.process.custom_workload
    traces = config.memory.traces
    workload_count = len(workload) if workload else 0
    trace_count = len(traces) if traces else 0
    return f"Custom workload: {workload_count} processes · Traces configured for {trace_count} processes" if workload_count or trace_count else "Using baseline workload."

VIEW = ManagerView(
    name="Scenario Builder",
    manager="Process",
    describe_config=describe_config,
    render_content=render_scenario_builder,
)
