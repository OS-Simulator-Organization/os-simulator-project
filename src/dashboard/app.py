import streamlit as st

from src.core.controller_api import ControllerAPI
from src.dashboard.config_sidebar import render_global_settings, render_load_panel
from src.dashboard.manager_view import render_manager_tab, render_sidebar_section
#from src.dashboard.mock_controller import MockController
from src.core.controller import RealController
from src.dashboard.views import VIEWS
from src.dashboard.views.comparison import render_comparison

TABS = [
    "Overview",
    *[view.name for view in VIEWS],
    "Testing Center",
    "Comparison",
]


def get_controller() -> ControllerAPI:
    if "controller" not in st.session_state:
        st.session_state.controller = RealController()
    return st.session_state.controller


def render_sidebar(controller: ControllerAPI) -> None:
    with st.sidebar:
        st.header("Run configuration")
        with st.expander("Global", expanded=True):
            render_global_settings()
        for view in VIEWS:
            render_sidebar_section(view)
        st.divider()
        render_load_panel(controller)

def render_overview() -> None:
    st.subheader("OS Simulator Overview")
    st.markdown("""
    Welcome to the **OS Simulator**. This platform models operating system subsystems in real time and demonstrates cross-manager execution dynamics.

    ### Subsystems Supported
    * **Process Subsystem:** Models CPU scheduling algorithms (Round Robin, FCFS, Priority, SJF), context switching, and Gantt charts.
    * **Memory Subsystem:** Simulates virtual memory paging, page fault handling, frame allocations, and replacement policies (FIFO, LRU).
    * **File Subsystem:** Manages hierarchical file trees, permissions, file creation/deletion, and dynamic I/O request queues.
    * **Event Engine:** Dispatches synchronized simulation ticks across all managers and streams real-time `EventRecord` logs.

    ---
    ### Quick Start
    1. Select a **Scenario** (e.g., `baseline`) in the **Global** sidebar panel.
    2. Click **Load and reset** to initialize the simulation engine.
    3. Step or run the engine using the playback controls on any manager view.
    """) 


def render_placeholder(name: str) -> None:
    st.subheader(name)
    st.info(f"The {name} view is coming soon.")


def main() -> None:
    st.set_page_config(page_title="OS Simulator", layout="wide")
    controller = get_controller()
    render_sidebar(controller)
    snapshot = controller.snapshot()
    events = st.session_state.get("events", [])

    st.title("OS Simulator")

    views = {view.name: view for view in VIEWS}
    for tab, name in zip(st.tabs(TABS), TABS):
        with tab:
            if name == "Overview":
                render_overview()
            elif name in views:
                render_manager_tab(views[name], snapshot, events)
            elif name == "Comparison":
                render_comparison()
            else:
                render_placeholder(name)
