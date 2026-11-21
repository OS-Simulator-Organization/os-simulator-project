"""Run / Pause / Step / Run-to-end / Reset buttons shared by every manager tab.

`prefix` keeps each tab's widget keys and autoplay flag separate (e.g. "process-step").
The run speed and the optional stop tick are global settings, set once above the tabs
by render_simulation_settings(), so every tab runs the same way.
"""

import time
from typing import Optional

import streamlit as st

from src.core.controller_api import RunStatus, Snapshot

SPEED = "sim-speed"          # ticks per second while Run is playing
USE_STOP = "sim-use-stop"    # whether runs stop at STOP_AT
STOP_AT = "sim-stop-at"      # stop condition: the tick to stop at
SPEED_OPTIONS = [1, 2, 4, 8]
MAX_RUN_TICKS = 10_000       # safety cap for "Run to completion"
CAPPED = "sim-run-capped"    # warning shown when the cap stopped a run


def render_simulation_settings() -> None:
    speed, toggle, stop = st.columns([3, 2, 2], vertical_alignment="bottom")
    speed.select_slider("Run speed (ticks per second)", options=SPEED_OPTIONS, value=1, key=SPEED)
    toggle.checkbox("Stop at a tick", key=USE_STOP, help="Run and Run to completion pause at this tick.")
    stop.number_input("Stop tick (ms)", min_value=1, value=20, step=1, key=STOP_AT,
                      disabled=not st.session_state.get(USE_STOP, False))


def stop_tick() -> Optional[int]:
    return st.session_state.get(STOP_AT, 20) if st.session_state.get(USE_STOP, False) else None


def _record(events: list) -> None:
    st.session_state.events = [*st.session_state.get("events", []), *events]
    st.rerun()


def _autoplay(controller, prefix: str) -> None:
    interval = 1 / st.session_state.get(SPEED, 1)

    @st.fragment(run_every=interval)
    def tick() -> None:
        # The full rerun that each step triggers also calls this; skip it so steps stay one interval apart.
        last_step = f"{prefix}-last-step"
        if time.monotonic() - st.session_state.get(last_step, 0.0) < interval * 0.9:
            return
        st.session_state[last_step] = time.monotonic()
        limit = stop_tick()
        if limit is not None and controller.snapshot().tick >= limit:
            st.session_state[f"{prefix}-autoplay"] = False
            controller.pause()
            st.rerun()
        _record(controller.step().events)

    tick()


def render_run_controls(controller, snapshot: Snapshot, prefix: str) -> None:
    autoplay = f"{prefix}-autoplay"
    can_advance = snapshot.status in (RunStatus.READY, RunStatus.PAUSED)
    if not can_advance:
        st.session_state[autoplay] = False
    playing = st.session_state.get(autoplay, False)

    with st.container(horizontal=True):
        if st.button("", icon=":material/play_arrow:", key=f"{prefix}-run", disabled=not can_advance or playing,
                     help="Run (steps at the chosen speed)"):
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
                     help="Run to completion, or to the stop tick if one is set"):
            st.session_state[autoplay] = False
            # A process that never unblocks would make an unlimited run loop forever, so cap it.
            limit = stop_tick() or snapshot.tick + MAX_RUN_TICKS
            result = controller.run(until_tick=limit)
            if stop_tick() is None and result.snapshot.status is not RunStatus.FINISHED:
                st.session_state[CAPPED] = f"Run stopped after {MAX_RUN_TICKS} ticks without finishing. Some processes may be blocked forever; check the Process state timeline."
            _record(result.events)
        if st.button("", icon=":material/replay:", key=f"{prefix}-reset",
                     disabled=snapshot.status == RunStatus.NOT_LOADED, help="Reset"):
            st.session_state[autoplay] = False
            st.session_state.pop(CAPPED, None)
            controller.reset()
            st.session_state.events = []
            st.rerun()

    status = "running" if playing else snapshot.status.value
    st.markdown(f"**Current Simulation Tick:** `{snapshot.tick} ms` · **Status:** `{status}`")
    if st.session_state.get(CAPPED) and snapshot.status is RunStatus.PAUSED:
        st.warning(st.session_state[CAPPED], icon=":material/warning:")
    if playing:
        _autoplay(controller, prefix)
