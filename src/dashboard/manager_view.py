"""Shared layout for every manager tab (#10).

Each manager tab is a ManagerView passed to render_manager_tab, so all tabs
share the same sections in the same order.
"""

from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

import pandas as pd
import streamlit as st

from src.core.controller_api import RunConfig, Snapshot
from src.core.events import EventRecord
from src.dashboard.test_runner import run_tests


@dataclass(frozen=True)
class ManagerView:
    """`manager` is the schema's manager value, used to pick this manager's
    metrics and events. `actions` render as disabled buttons until wired up.
    `test_files` are the pytest files the tab's "Run tests" button runs."""

    name: str
    manager: str
    regions: Tuple[str, ...] = ()
    actions: Tuple[str, ...] = ()
    describe_config: Optional[Callable[[RunConfig], str]] = None
    render_sidebar: Optional[Callable[[], None]] = None
    render_content: Optional[Callable[[Snapshot], None]] = None
    test_files: Tuple[str, ...] = ()

def render_manager_tab(view: ManagerView, snapshot: Snapshot, events: List[EventRecord]) -> None:
    _render_header(view, snapshot)
    _render_test_results(view)
    _render_metrics(view, snapshot)
    if view.render_content:
        view.render_content(snapshot)
    else:
        for region in view.regions:
            with st.container(border=True):
                st.markdown(f"**{region}**")
                st.caption("Coming soon.")
    with st.expander("Inputs"):
        st.caption("Not editable yet.")
    with st.expander("Event log"):
        own_events = [e.to_dict() for e in events if e.manager == view.manager]
        if own_events:
            st.dataframe(own_events, hide_index=True)
        else:
            st.caption("No events yet.")
        _render_exports(view, snapshot, own_events)


def events_csv(events: List[dict]) -> str:
    return pd.DataFrame(events).to_csv(index=False)


def metrics_csv(manager: str, snapshot: Snapshot) -> str:
    rows = [{"manager": manager, "metric": key, "value": metric.value, "unit": metric.unit}
            for key, metric in snapshot.metrics.get(manager, {}).items()]
    return pd.DataFrame(rows, columns=["manager", "metric", "value", "unit"]).to_csv(index=False)


def _render_exports(view: ManagerView, snapshot: Snapshot, own_events: List[dict]) -> None:
    name = view.name.lower().replace(" ", "_")
    events_col, metrics_col = st.columns(2)
    events_col.download_button("Download event log (CSV)", events_csv(own_events), f"{name}_events.csv",
                               "text/csv", key=f"{view.name}-events-csv", disabled=not own_events)
    metrics_col.download_button("Download metrics (CSV)", metrics_csv(view.manager, snapshot), f"{name}_metrics.csv",
                                "text/csv", key=f"{view.name}-metrics-csv",
                                disabled=not snapshot.metrics.get(view.manager))


def render_sidebar_section(view: ManagerView) -> None:
    with st.expander(view.name):
        if view.render_sidebar:
            view.render_sidebar()
        else:
            st.caption("Not configurable yet.")


def _render_header(view: ManagerView, snapshot: Snapshot) -> None:
    title, actions = st.columns([3, 1])
    title.subheader(view.name)
    if view.test_files and actions.button(f"Run {view.name.lower()} tests", key=f"{view.name}-run-tests"):
        with st.spinner(f"Running {view.name.lower()} tests..."):
            st.session_state[f"{view.name}-test-run"] = run_tests(view.test_files)
    for action in view.actions:
        actions.button(action, key=f"{view.manager}-{action}", disabled=True, help="Not functional yet.")
    if view.describe_config:
        st.caption(view.describe_config(snapshot.config))
    else:
        st.caption("Not configurable yet.")


def _render_test_results(view: ManagerView) -> None:
    test_run = st.session_state.get(f"{view.name}-test-run")
    if test_run is None:
        return
    if test_run.passed:
        st.success(f"Tests passed: {test_run.summary}", icon=":material/check_circle:")
    else:
        st.error(f"Tests failed: {test_run.summary}", icon=":material/error:")
    if test_run.results:
        st.dataframe(test_run.results, hide_index=True)
    with st.expander("Full pytest output"):
        st.code(test_run.output, language="text")


def _render_metrics(view: ManagerView, snapshot: Snapshot) -> None:
    if view.manager == "None":
        return
    
    raw_metrics = snapshot.metrics.get(view.manager, {})
    if not raw_metrics:
        st.caption("No metrics yet. Load a run to see them.")
        return
    
    metrics = list(raw_metrics.items()) if isinstance(raw_metrics, dict) else list(raw_metrics)        
    # Group metrics into rows of 4 columns
    chunk_size = 4
    for i in range(0, len(metrics), chunk_size):
        chunk = metrics[i:i + chunk_size]
        cols = st.columns(chunk_size)
        for col, (key, metric) in zip(cols, chunk):
            val = metric.value
            if val.is_integer():
                val_str = f"{int(val)}"
            else:
                val_str = f"{val:.2f}"

            label = key.replace("_", " ").capitalize()

            # Render custom card for each metric
            with col:
                st.markdown(
                    f"""
                    <div style="
                        padding: 10px 12px;
                        border-radius: 6px;
                        border: 1px solid rgba(150, 150, 150, 0.2);
                        background-color: rgba(150, 150, 150, 0.03);
                        margin-bottom: 10px;
                    ">
                        <div style="font-size: 0.75rem; color: gray; font-weight: 500; margin-bottom: 2px;">{label}</div>
                        <div style="font-size: 1.15rem; font-weight: 600;">{val_str} <span style="font-size: 0.8rem; font-weight: normal; color: gray;">{metric.unit}</span></div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )