import streamlit as st

from src.core.controller_api import ControllerAPI
from src.dashboard.mock_controller import MockController

MANAGERS = [
    "Process",
    "Memory",
    "File System",
    "Security",
    "Device",
    "Network",
    "Parallel"
]
TABS = [
    "Overview",
    *MANAGERS,
    "Scenario Builder",
    "Testing Center",
    "Comparison"
]

def get_controller() -> ControllerAPI:
    if "controller" not in st.session_state:
        st.session_state.controller = MockController()
    return st.session_state.controller


def render_sidebar() -> None:
    with st.sidebar:
        st.header("Run configuration")
        with st.expander("Global", expanded=True):
            st.caption("Not configurable yet.")
        for manager in MANAGERS:
            with st.expander(manager):
                st.caption("Not configurable yet.")


def render_placeholder(name: str) -> None:
    st.subheader(name)
    st.info(f"The {name} view is coming soon.")


def main() -> None:
    st.set_page_config(page_title="OS Simulator", layout="wide")
    get_controller()

    st.title("OS Simulator")
    st.caption("Currently only running on a mock, scripted FCFS run of three processes.")
    render_sidebar()

    for tab, name in zip(st.tabs(TABS), TABS):
        with tab:
            render_placeholder(name)
