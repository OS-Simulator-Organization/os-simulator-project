import json
import pandas as pd
import streamlit as st
from typing import Any, Dict, List
from src.dashboard.manager_view import ManagerView
from src.core.controller_api import RunConfig, Snapshot

DEFAULT_WORKLOAD = [
    {"pid": "P1", "arrival_time": 0, "burst_time": 8, "priority": 3, "owner_id": "user1"},
    {"pid": "P2", "arrival_time": 1, "burst_time": 4, "priority": 1, "owner_id": "user1"},
]
REQUIRED_COLUMNS = ["pid", "arrival_time", "burst_time"]

def validate_workload(df: pd.DataFrame) -> List[str]:
    if df.empty:
        return ["Workload cannot be empty."]
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        return [f"Missing required column(s): {', '.join(missing)}."]

    errors = []
    if not df["pid"].is_unique:
        errors.append("Process IDs must be unique.")
    # Imported files can hold text in number columns; treat it as missing.
    arrival = pd.to_numeric(df["arrival_time"], errors="coerce")
    burst = pd.to_numeric(df["burst_time"], errors="coerce")
    for i, pid in enumerate(df["pid"]):
        if pd.isna(pid) or not str(pid).strip():
            errors.append(f"Row {i + 1}: Process ID cannot be empty.")
            pid = f"Row {i + 1}"
        if pd.isna(arrival.iloc[i]) or arrival.iloc[i] < 0:
            errors.append(f"{pid}: Arrival time must be >= 0.")
        if pd.isna(burst.iloc[i]) or burst.iloc[i] <= 0:
            errors.append(f"{pid}: Burst time must be > 0.")
    return errors

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

    st.write("Double-click cells to edit. Use the bottom empty row to add. Select rows to delete.")
    edited_df = st.data_editor(
        state.current_workload,
        num_rows="dynamic",
        width="stretch",
        key=f"process_editor_{state.editor_version}",
    )

    if st.button("Validate & Apply Scenario", type="primary"):
        errors = validate_workload(edited_df)
        if errors:
            for err in errors:
                st.error(err)
        else:
            state["custom_workload"] = to_workload(edited_df)
            st.success("Scenario validated! Press Load and reset in the sidebar to run it.")

def describe_config(config: RunConfig) -> str:
    workload = config.process.custom_workload
    return f"Custom workload: {len(workload)} processes" if workload else "Using the baseline workload."

VIEW = ManagerView(
    name="Scenario Builder",
    manager="Process",
    describe_config=describe_config,
    render_content=render_scenario_builder,
)
