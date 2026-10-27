# from src.core.controller_api import RunConfig
# from src.dashboard.config_sidebar import render_process_settings
# from src.dashboard.manager_view import ManagerView


# def describe_config(config: RunConfig) -> str:
#     process = config.process
#     quantum = f"{process.quantum_ms} ms" if process.quantum_ms is not None else "-"
#     return f"Policy: {process.policy.value} · Quantum: {quantum} · Context switch: {process.context_switch_ms} ms"


# VIEW = ManagerView(
#     name="Process",
#     manager="Process",
#     regions=("CPU Gantt chart", "Process table"),
#     actions=("Run process tests",),
#     describe_config=describe_config,
#     render_sidebar=render_process_settings,
# )

import streamlit as st
from src.core.controller_api import RunConfig, RunStatus, Snapshot
from src.dashboard.config_sidebar import render_process_settings
from src.dashboard.manager_view import ManagerView


def describe_config(config: RunConfig) -> str:
    process = config.process
    quantum = f"{process.quantum_ms} ms" if process.quantum_ms is not None else "N/A"
    return f"Policy: {process.policy.value} · Quantum: {quantum} · Context switch: {process.context_switch_ms} ms"


def render_process_content(snapshot: Snapshot) -> str:
    controller = st.session_state.get("controller")
    if not controller or not hasattr(controller, "engine"):
        st.warning("Controller not initialized.")
        return

    proc_mgr = controller.engine.get_manager("Process")
    if not proc_mgr:
        st.info("Process manager not registered.")
        return

    # Simulation Execution Controls (Step / Run)
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("Step (1 tick)", disabled=snapshot.status != RunStatus.READY):
            controller.step()
            st.rerun()
    with col2:
        if st.button("Run to completion", disabled=snapshot.status != RunStatus.READY):
            controller.run()
            st.rerun()
    with col3:
        st.markdown(f"**Current Simulation Tick:** `{snapshot.tick} ms`")

    # Pull process manager state snapshot
    mgr_state = proc_mgr.snapshot()

    # Region 1: CPU Gantt Chart
    with st.container(border=True):
        st.markdown("**CPU Gantt chart**")
        gantt_csv = proc_mgr._gantt_chart()
        if proc_mgr.gantt_ticks:
            st.code(gantt_csv, language="csv")
        else:
            st.caption("No CPU execution recorded yet. Press Step or Run.")

    # Region 2: Process Table & Ready Queue
    with st.container(border=True):
        st.markdown("**Process Table & Workload Status**")
        workload_data = mgr_state.get("workload", [])
        if workload_data:
            st.dataframe(workload_data, hide_index=True)
        else:
            st.caption("No processes loaded.")


VIEW = ManagerView(
    name="Process",
    manager="Process",
    regions=("CPU Gantt chart", "Process table"),
    actions=("Run process tests",),
    describe_config=describe_config,
    render_sidebar=render_process_settings,
    render_content=render_process_content,
)