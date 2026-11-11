"""Run / Pause / Step / Run-to-end / Reset buttons for a manager tab.

Same behavior and look as the controls in the Process and Memory tabs; `prefix`
keeps each tab's widget keys and autoplay flag separate.
"""

import time

import streamlit as st

from src.core.controller_api import RunStatus, Snapshot


def _record(events: list) -> None:
    st.session_state.events = [*st.session_state.get("events", []), *events]
    st.rerun()


@st.fragment(run_every=1)
def _autoplay(controller, prefix: str) -> None:
    # The full rerun that each step triggers also calls this; skip it so steps stay a second apart.
    last_step = f"{prefix}-last-step"
    if time.monotonic() - st.session_state.get(last_step, 0.0) < 0.9:
        return
    st.session_state[last_step] = time.monotonic()
    _record(controller.step().events)


def render_run_controls(controller, snapshot: Snapshot, prefix: str) -> None:
    autoplay = f"{prefix}-autoplay"
    can_advance = snapshot.status in (RunStatus.READY, RunStatus.PAUSED)
    if not can_advance:
        st.session_state[autoplay] = False
    playing = st.session_state.get(autoplay, False)

    with st.container(horizontal=True):
        if st.button("", icon=":material/play_arrow:", key=f"{prefix}-run", disabled=not can_advance or playing,
                     help="Run (one tick per second)"):
            st.session_state[autoplay] = True
            st.rerun()
        if st.button("", icon=":material/pause:", key=f"{prefix}-pause", disabled=not playing, help="Pause"):
            st.session_state[autoplay] = False
            controller.pause()
            st.rerun()
        if st.button("", icon=":material/skip_next:", key=f"{prefix}-step", disabled=not can_advance or playing,
                     help="Step (1 tick)"):
            _record(controller.step().events)
        if st.button("", icon=":material/fast_forward:", key=f"{prefix}-run-to-end", disabled=not can_advance,
                     help="Run to completion"):
            st.session_state[autoplay] = False
            _record(controller.run().events)
        if st.button("", icon=":material/replay:", key=f"{prefix}-reset",
                     disabled=snapshot.status == RunStatus.NOT_LOADED, help="Reset"):
            st.session_state[autoplay] = False
            controller.reset()
            st.session_state.events = []
            st.rerun()

    status = "running" if playing else snapshot.status.value
    st.markdown(f"**Current Simulation Tick:** `{snapshot.tick} ms` · **Status:** `{status}`")
    if playing:
        _autoplay(controller, prefix)
