"""Shared layout for every manager tab (#10).

Each manager tab is a ManagerView passed to render_manager_tab, so all tabs
share the same sections in the same order.
"""

from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

import streamlit as st

from src.core.controller_api import RunConfig, Snapshot
from src.core.events import EventRecord


@dataclass(frozen=True)
class ManagerView:
    """`manager` is the schema's manager value, used to pick this manager's
    metrics and events. `actions` render as disabled buttons until wired up."""

    name: str
    manager: str
    regions: Tuple[str, ...] = ()
    actions: Tuple[str, ...] = ()
    describe_config: Optional[Callable[[RunConfig], str]] = None
    render_sidebar: Optional[Callable[[], None]] = None
    render_content: Optional[Callable[[Snapshot], None]] = None

def render_manager_tab(view: ManagerView, snapshot: Snapshot, events: List[EventRecord]) -> None:
    _render_header(view, snapshot)
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


def render_sidebar_section(view: ManagerView) -> None:
    with st.expander(view.name):
        if view.render_sidebar:
            view.render_sidebar()
        else:
            st.caption("Not configurable yet.")


def _render_header(view: ManagerView, snapshot: Snapshot) -> None:
    title, actions = st.columns([3, 1])
    title.subheader(view.name)
    for action in view.actions:
        actions.button(action, key=f"{view.manager}-{action}", disabled=True, help="Not functional yet.")
    if view.describe_config:
        st.caption(view.describe_config(snapshot.config))
    else:
        st.caption("Not configurable yet.")


def _render_metrics(view: ManagerView, snapshot: Snapshot) -> None:
    raw_metrics = snapshot.metrics.get(view.manager, {})
    if not raw_metrics:
        st.caption("No metrics yet. Load a run to see them.")
        return
    
    metrics = list(raw_metrics.items()) if isinstance(raw_metrics, dict) else list(raw_metrics)

    # Remove redundant metrics
    filtered_metrics = []
    excluded_metrics = ["page_hits", "page_faults", "page_hit_rate", "avg_access_time"]
    for key, metric in metrics:
        if key not in excluded_metrics:
            filtered_metrics.append((key, metric))
    metrics = filtered_metrics
        
    
    # Group metrics into rows of 4 columns
    chunk_size = 4
    for i in range(0, len(metrics), chunk_size):
        chunk = metrics[i:i + chunk_size]
        cols = st.columns(len(chunk))
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