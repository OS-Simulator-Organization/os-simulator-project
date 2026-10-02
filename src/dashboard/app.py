import streamlit as st

from src.core.controller_api import ControllerAPI
from src.dashboard.manager_view import render_manager_tab, render_sidebar_section
from src.dashboard.mock_controller import MockController
from src.dashboard.views import VIEWS

TABS = [
    "Overview",
    *[view.name for view in VIEWS],
    "Scenario Builder",
    "Testing Center",
    "Comparison",
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
        for view in VIEWS:
            render_sidebar_section(view)


def render_placeholder(name: str) -> None:
    st.subheader(name)
    st.info(f"The {name} view is coming soon.")


def main() -> None:
    st.set_page_config(page_title="OS Simulator", layout="wide")
    snapshot = get_controller().snapshot()
    events = st.session_state.get("events", [])

    st.title("OS Simulator")
    st.caption("Currently only running on a mock, scripted FCFS run of three processes.")
    render_sidebar()

    views = {view.name: view for view in VIEWS}
    for tab, name in zip(st.tabs(TABS), TABS):
        with tab:
            if name in views:
                render_manager_tab(views[name], snapshot, events)
            else:
                render_placeholder(name)
