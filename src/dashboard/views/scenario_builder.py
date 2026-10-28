import json
import pandas as pd
import streamlit as st
from typing import List
from src.dashboard.manager_view import ManagerView
from src.core.controller_api import Snapshot

DEFAULT_WORKLOAD = [
    {"pid": "P1", "arrival_time": 0, "burst_time": 8, "priority": 3, "owner_id": "user1"},
    {"pid": "P2", "arrival_time": 1, "burst_time": 4, "priority": 1, "owner_id": "user1"},
]

def validate_workload(df: pd.DataFrame) -> List[str]:
    errors = []
    if df.empty:
        return ["Workload cannot be empty."]
    if not df["pid"].is_unique:
        errors.append("Process IDs must be unique.")
    for idx, row in df.iterrows():
        pid = row.get("pid", f"Row {idx}")
        if pd.isna(row.get("arrival_time")) or row["arrival_time"] < 0:
            errors.append(f"{pid}: Arrival time must be >= 0.")
        if pd.isna(row.get("burst_time")) or row["burst_time"] <= 0:
            errors.append(f"{pid}: Burst time must be > 0.")
    return errors

def render_scenario_builder(view: ManagerView, snapshot: Snapshot, events: list) -> None:
    st.subheader("Scenario Builder")
    st.caption("Add, edit, remove, import, and validate custom workloads.")

    if "current_workload" not in st.session_state:
        st.session_state.current_workload = pd.DataFrame(DEFAULT_WORKLOAD)

    uploaded_file = st.file_uploader("Import Workload (JSON/CSV)", type=["json", "csv"])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.DataFrame(json.load(uploaded_file))
            st.session_state.current_workload = df
            st.success("File imported successfully!")
        except Exception as e:
            st.error(f"Import failed: {e}")

    st.write("Double-click cells to edit. Use the bottom empty row to add. Select rows to delete.")
    edited_df = st.data_editor(
        st.session_state.current_workload, 
        num_rows="dynamic", 
        use_container_width=True,
        key="process_editor"
    )
    st.session_state.current_workload = edited_df

    if st.button("Validate & Apply Scenario", type="primary"):
        errors = validate_workload(edited_df)
        if errors:
            for err in errors:
                st.error(err)
        else:
            st.session_state["custom_workload"] = edited_df.to_dict(orient="records")
            st.success("Scenario validated! Your next run will use this workload.")

VIEW = ManagerView(
    name="Scenario Builder",
    manager="Process",
    render_sidebar=None,
)