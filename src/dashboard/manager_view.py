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


def render_manager_tab(view: ManagerView, snapshot: Snapshot, events: List[EventRecord]) -> None:
    _render_header(view, snapshot)
    _render_metrics(view, snapshot)
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
    metrics = snapshot.metrics.get(view.manager, {})
    if not metrics:
        st.caption("No metrics yet. Load a run to see them.")
        return
    for column, (key, metric) in zip(st.columns(len(metrics)), metrics.items()):
        column.metric(key.replace("_", " ").capitalize(), f"{metric.value:g} {metric.unit}")
